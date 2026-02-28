from odoo import api, models, fields
from collections import defaultdict
from datetime import date, timedelta

class ReportTimesheetInterim(models.AbstractModel):
    """
    QWeb report backend for the CRA (timesheet) PDF.

    This AbstractModel is called by Odoo when rendering the QWeb template whose
    `report_name` matches this model name WITHOUT the leading "report.".

    Design goals:
    - Wizard is the single source of truth for the period (date_from/date_to) and filtering.
    - We fetch analytic lines (work) and HR leaves (absence) to build a day-by-day grid.
    - We explicitly ignore "Time Off" generated analytic lines so leave days do not appear as worked.
    """

    _name = "report.achmitech_portal_timesheets.cra_report"
    _description = "Timesheet CRA Interim Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Entry point for QWeb report rendering.

        Parameters
        ----------
        docids : list[int]
            The record ids passed to `report_action`. We DO NOT rely on docids to define
            the report content; the wizard `data` is the source of truth.
        data : dict | None
            Parameters passed from the wizard (employee_id, date_from, date_to, optional filters).

        Returns
        -------
        dict
            Context passed to QWeb template:
            - employee: hr.employee record (or False)
            - period_start / period_end: date boundaries coming from wizard
            - values: precomputed structures for rendering (days/months/total_cra)
            - docs/doc_ids/doc_model: kept for QWeb compatibility/debugging
        """

        data = data or {}
        
        employee_id = data.get("employee_id")
        date_from = fields.Date.to_date(data.get("date_from"))
        date_to = fields.Date.to_date(data.get("date_to"))

        # If the wizard didn't pass valid parameters, return an empty payload.
        # This avoids hard crashes in QWeb and makes failures obvious in the PDF (empty tables).
        if not employee_id or not date_from or not date_to:
            # If wizard didn't pass data, fail cleanly
            return {
                "doc_ids": [],
                "doc_model": "account.analytic.line",
                "docs": self.env["account.analytic.line"],
                "data": data,
                "employee": False,
                "values": {"days": [], "months": [], "total_cra": 0},
                "period_start": date_from,
                "period_end": date_to,
                "client": False
            }

        employee = self.env["hr.employee"].browse(employee_id).exists()

        # Source of truth: domain based on wizard (NOT docids).
        # company_id is scoped to the employee's company so cross-company lines never bleed in.
        domain = [
            ("employee_id", "=", employee_id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("company_id", "=", employee.company_id.id),
        ]

        # Optional filters: only include lines for the selected project/task.
        if data.get("project_id"):
            domain.append(("project_id", "=", data["project_id"]))

        if data.get("task_id"):
            domain.append(("task_id", "=", data["task_id"]))

        lines = self.env["account.analytic.line"].search(domain, order="date asc")

        # Build rendering values (calendar grid + leave overlay + totals).
        values = self._compute_timesheet_values(lines, employee, date_from, date_to)
        conges_previsionnels = self._compute_conges_previsionnels(employee, date_from)

        # Project comes from the wizard
        project = self.env["project.project"].browse(data.get("project_id")).exists()

        # Client is the partner linked to the project
        client = project.partner_id if project else False

        return {
            "doc_ids": lines.ids,
            "doc_model": "account.analytic.line",
            "docs": lines,
            "data": data,
            "employee": employee,
            "values": values,
            "project": project,
            "client": client,
            "conges_previsionnels": conges_previsionnels,
            "period_start": date_from,
            "period_end": date_to,
        }

    def _is_timeoff_line(self, l):
        """
        Identify timesheet lines automatically created for time off.

        Why:
        - When a leave is approved, Odoo may create an `account.analytic.line`
          (often 8h) on a "Time Off"/"Congé" task/project.
        - If we treat those hours as worked hours, leave days become green and CRA becomes 1,
          which is misleading for a CRA "temps travaillé".

        Current heuristic:
        - Match task/project names containing "time off" or "congé".
        - If you have stable IDs (time off project/task), prefer excluding by ID for reliability.

        Returns
        -------
        bool
            True if the line looks like an absence-generated line that should not count as worked.
        """

        task_name = (l.task_id.name or "").lower() if l.task_id else ""
        proj_name = (l.project_id.name or "").lower() if l.project_id else ""
        return ("time off" in task_name) or ("time off" in proj_name) or ("congé" in task_name) or ("congé" in proj_name)

    
    def _compute_timesheet_values(self, lines, employee, period_start, period_end):
        """
        Build the day-by-day CRA grid for the selected period.

        Inputs
        ------
        lines : recordset(account.analytic.line)
            Timesheet lines filtered by employee + date range (+ optional project/task filters).
        employee : recordset(hr.employee) | False
            Employee for which the report is generated.
        period_start, period_end : date
            Period boundaries coming from the wizard.

        Output structure (returned dict)
        -------------------------------
        - days: list[dict]
            One dict per calendar day in the period with:
            label, cra_value, bg, status_code
        - months: list[dict]
            Next 3 months header labels for the "congés prévisionnels" table.
        - total_cra: float
            Sum of daily CRA values.

        Rules implemented
        -----------------
        - Work hours are aggregated per day from `account.analytic.line`, excluding time off lines.
        - Leaves (hr.leave) and public holidays (resource.calendar.leaves) overlay the calendar.
        - Color priority: worked (green) > overlay (leave/holiday color) > weekend (grey) > absent (red).
        - If a day has an overlay AND worked hours = 0, CRA is forced to 0 and status_code can show.
        """


        # build all dates from wizard range
        all_dates = []
        cur = period_start
        while cur <= period_end:
            all_dates.append(cur)
            cur += timedelta(days=1)

        # aggregate hours per date
        hours_by_date = defaultdict(float)
        timeoff_hours_by_date = defaultdict(float)

        for l in lines:
            if self._is_timeoff_line(l):
                timeoff_hours_by_date[l.date] += (l.unit_amount or 0.0)
            else:
                hours_by_date[l.date] += (l.unit_amount or 0.0)

        def cra_from_hours(h):
            """Business rule: CRA = 1 if >4h, 0.5 if >0h, else 0."""
            return 1 if h > 4 else (0.5 if h > 0 else 0)

        # Build overlay map: date -> info (CONGE/MALADIE/FERIE)
        overlay_by_date = {}
        if employee:
            # Validated leaves that overlap the selected period, scoped to the employee's company.
            leaves = self.env["hr.leave"].sudo().search([
                ("employee_id", "=", employee.id),
                ("company_id", "=", employee.company_id.id),
                ("state", "=", "validate"),
                ("request_date_from", "<=", period_end),
                ("request_date_to", ">=", period_start),
            ])

            for lv in leaves:
                d0, d1 = lv.request_date_from, lv.request_date_to
                if not d0 or not d1:
                    continue
                lt = lv.holiday_status_id.display_name or ""
                lt_low = lt.lower()
                info = {"code": "MALADIE", "label": lt, "color": "#F4B183"} if ("malad" in lt_low or "sick" in lt_low) \
                       else {"code": "CONGE", "label": lt, "color": "#00B0F0"}
                
                cur = max(d0, period_start)
                end = min(d1, period_end)
                while cur <= end:
                    overlay_by_date[cur] = info
                    cur += timedelta(days=1)

            # Public holidays: include leaves from the employee's company OR with no company
            # (global holidays). Leaves from other companies are excluded.
            cal_leaves = self.env["resource.calendar.leaves"].sudo().search([
                ("company_id", "in", [employee.company_id.id, False]),
                ("date_from", "<=", fields.Datetime.to_datetime(period_end)),
                ("date_to", ">=", fields.Datetime.to_datetime(period_start)),
            ])
            for hl in cal_leaves:
                cur = fields.Date.to_date(hl.date_from)
                end = fields.Date.to_date(hl.date_to)
                while cur <= end:
                    overlay_by_date.setdefault(cur, {"code": "FÉRIÉ", "label": hl.name or "Férié", "color": "#FFD966"})
                    cur += timedelta(days=1)

        # Render-friendly list for QWeb
        day_names = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche']
        days = []
        total_cra = 0

        for d in all_dates:
            weekday = day_names[d.weekday()]
            is_weekend = d.weekday() in (5, 6)

            h = hours_by_date[d]
            overlay = overlay_by_date.get(d)

            cra = cra_from_hours(h)

            # rule: leave/holiday days show 0 if not worked
            if h <= 0 and overlay:
                cra = 0

            # Show a code only when there is an overlay and there are no worked hours.
            status_code = overlay["code"] if (overlay and h <= 0) else ""

            total_cra += cra

            # Background color selection (priority order)
            if h > 0:
                bg = "#78db7d"
            elif overlay:
                bg = overlay["color"]
            elif is_weekend:
                bg = "#b4b4b4"
            else:
                bg = "#ed3a3a"

            days.append({
                "label": f"{weekday}-{d.day}",
                "cra_value": cra,
                "bg": bg,
                "status_code": status_code,  # or (overlay["code"] if overlay and h <= 0 else "")
            })

        # Header for "congés prévisionnels": next 3 months starting from period_start month.
        month_names_fr = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                          'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

        p_month = period_start.month
        p_year = period_start.year

        months = []
        for i in (1, 2, 3):
            mn = ((p_month + i - 1) % 12) + 1
            yy = p_year + ((p_month + i - 1) // 12)
            months.append({"name": month_names_fr[mn], "year": yy})

        return {"days": days, "months": months, "total_cra": total_cra}
    

    def _compute_conges_previsionnels(self, employee, period_start):
        """
        Returns a list of 3 dicts: [{name, year, planned_days}, ...]
        planned_days = number of leave days (pending+approved) that overlap each month.
        """
        month_names_fr = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

        # Your logic: next 3 months starting from period_start.month (i = 1..3)
        p_month = period_start.month
        p_year = period_start.year

        months = []
        for i in (1, 2, 3):
            mn = ((p_month + i - 1) % 12) + 1
            yy = p_year + ((p_month + i - 1) // 12)
            months.append({"month": mn, "year": yy, "name": month_names_fr[mn], "planned_days": 0})

        if not employee:
            return [{"name": m["name"], "year": m["year"], "planned_days": 0} for m in months]

        # Build month boundaries
        def month_start_end(y, m):
            start = date(y, m, 1)
            # next month start - 1 day
            if m == 12:
                end = date(y + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(y, m + 1, 1) - timedelta(days=1)
            return start, end

        # We fetch all leaves overlapping the total window (3 months)
        window_start, _ = month_start_end(months[0]["year"], months[0]["month"])
        _, window_end = month_start_end(months[2]["year"], months[2]["month"])

        leaves = self.env["hr.leave"].sudo().search([
            ("employee_id", "=", employee.id),
            ("company_id", "=", employee.company_id.id),
            ("state", "in", ("confirm", "validate1", "validate")),
            ("request_date_from", "<=", window_end),
            ("request_date_to", ">=", window_start),
        ])

        # Count per day per month (simple + robust)
        for lv in leaves:
            d0 = lv.request_date_from or fields.Date.to_date(lv.date_from)
            d1 = lv.request_date_to or fields.Date.to_date(lv.date_to)
            if not d0 or not d1:
                continue

            cur = max(d0, window_start)
            end = min(d1, window_end)
            while cur <= end:
                # Option: count only CONGE type (exclude MALADIE etc.)
                lt = (lv.holiday_status_id.display_name or "").lower()
                is_conge = not ("malad" in lt or "sick" in lt)
                if is_conge:
                    for m in months:
                        if cur.year == m["year"] and cur.month == m["month"]:
                            m["planned_days"] += 1
                            break
                cur += timedelta(days=1)

        return [{"name": m["name"], "year": m["year"], "planned_days": m["planned_days"]} for m in months]