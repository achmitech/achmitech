# -*- coding: utf-8 -*-
import calendar as cal_module
from markupsafe import Markup, escape
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.hr_timesheet.controllers.project import ProjectCustomerPortal as HrTimesheetProjectPortal

MONTH_NAMES_FR = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']


class AchPortalTimesheetTask(HrTimesheetProjectPortal):
    """Override task page view to show each employee their own timesheet lines.

    The standard portal domain for account.analytic.line filters by partner/message_partner_ids,
    which excludes interim workers' own lines. We replace timesheets with a direct
    employee-based query so they can see (and the validated field shows correctly).
    """

    def _task_get_page_view_values(self, task, access_token, **kwargs):
        values = super()._task_get_page_view_values(task, access_token, **kwargs)
        employee = request.env["hr.employee"].sudo().search([
            ("user_id", "=", request.env.user.id),
            ("company_id", "=", request.env.company.id),
        ], limit=1)
        if employee and task.project_id:
            values['timesheets'] = request.env['account.analytic.line'].sudo().search([
                ('task_id', '=', task.id),
                ('employee_id', '=', employee.id),
            ], order='date asc')
        return values


class PortalTimesheet(CustomerPortal):

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_employee_for_portal_user(self):
        return request.env["hr.employee"].sudo().search([
            ("user_id", "=", request.env.user.id),
            ("company_id", "=", request.env.company.id),
        ], limit=1)

    def _get_client_projects(self):
        """Projects where the current portal user is the client (project.partner_id)."""
        partner = request.env.user.partner_id
        return request.env["project.project"].sudo().search([
            ("partner_id", "=", partner.id),
            ("allow_timesheets", "=", True),
        ])

    def _task_redirect(self, task):
        url = task.get_portal_url()
        return request.redirect(url + "#task_timesheets")

    # ── Interim timesheet submission ───────────────────────────────────────────

    @http.route("/my/timesheets/create", type="http", auth="user", website=True, methods=["POST"])
    def portal_timesheet_create(self, **post):
        employee = self._get_employee_for_portal_user()
        if not employee:
            request.session["ts_flash"] = {"type": "danger", "message": "Aucun employé n'est associé à votre compte. Veuillez contacter l'administrateur."}
            return request.redirect("/my/tasks")

        task_id = int(post.get("task_id") or 0)
        date_str = (post.get("date") or "").strip()
        description = (post.get("name") or "").strip()

        task = request.env["project.task"].sudo().browse(task_id).exists()
        if not task:
            request.session["ts_flash"] = {"type": "danger", "message": "La tâche sélectionnée est introuvable ou n'est plus disponible."}
            return request.redirect("/my/tasks")

        try:
            ratio_str = (post.get("day_ratio") or "").strip()
            ratio = float(ratio_str)
        except Exception:
            request.session["ts_flash"] = {"type": "danger", "message": "Veuillez choisir 0, 0,5 ou 1."}
            return self._task_redirect(task)

        if ratio not in (0.0, 0.5, 1.0):
            request.session["ts_flash"] = {"type": "danger", "message": "Valeur invalide. Choisissez 0, 0,5 ou 1."}
            return self._task_redirect(task)

        if not date_str:
            request.session["ts_flash"] = {"type": "danger", "message": "Veuillez saisir une date valide."}
            return self._task_redirect(task)
        try:
            parsed_date = fields.Date.from_string(date_str)
        except Exception:
            request.session["ts_flash"] = {"type": "danger", "message": "Format de date invalide."}
            return self._task_redirect(task)

        project = task.project_id.sudo()
        if not project or not project.allow_timesheets:
            request.session["ts_flash"] = {"type": "danger", "message": "Cette tâche appartient à un projet qui n'autorise pas la saisie des feuilles de temps."}
            return self._task_redirect(task)

        if request.env.user not in task.user_ids:
            request.session["ts_flash"] = {"type": "danger", "message": "Vous n'êtes pas assigné(e) à cette tâche."}
            return self._task_redirect(task)

        if task.stage_id and task.stage_id.fold:
            request.session["ts_flash"] = {"type": "danger", "message": "Cette tâche est clôturée. Vous ne pouvez plus modifier vos feuilles de temps."}
            return self._task_redirect(task)

        existing = request.env["account.analytic.line"].sudo().search([
            ("employee_id", "=", employee.id),
            ("date", "=", parsed_date),
            ("task_id", "=", task.id),
            ("company_id", "=", request.env.company.id),
        ], limit=1)

        if existing and existing.validated:
            request.session["ts_flash"] = {"type": "danger", "message": "Cette saisie a déjà été validée par le client et ne peut plus être modifiée."}
            return self._task_redirect(task)

        unit_amount = ratio * 8.0

        if existing:
            existing.write({
                "name": description,
                "unit_amount": unit_amount,
                "project_id": project.id,
                "task_id": task.id,
            })
            request.session["ts_flash"] = {"type": "success", "message": "Votre saisie pour cette date a été mise à jour."}
        else:
            request.env["account.analytic.line"].sudo().create({
                "name": description,
                "date": parsed_date,
                "unit_amount": unit_amount,
                "project_id": project.id,
                "task_id": task.id,
                "employee_id": employee.id,
                "user_id": request.env.user.id,
                "company_id": request.env.company.id,
            })
            request.session["ts_flash"] = {"type": "success", "message": "Votre temps a été enregistré avec succès."}

        return self._task_redirect(task)

    # ── Client timesheet validation portal ────────────────────────────────────

    @http.route("/my/client-timesheets", type="http", auth="user", website=True)
    def portal_client_timesheets(self, month=None, year=None, **kwargs):
        projects = self._get_client_projects()

        today = fields.Date.today()
        try:
            sel_year = int(year) if year else today.year
            sel_month = int(month) if month else today.month
        except (ValueError, TypeError):
            sel_year, sel_month = today.year, today.month

        sel_month = max(1, min(12, sel_month))

        from datetime import date as dt_date
        date_from = dt_date(sel_year, sel_month, 1)
        date_to = dt_date(sel_year, sel_month, cal_module.monthrange(sel_year, sel_month)[1])

        groups = []
        if projects:
            lines = request.env["account.analytic.line"].sudo().search([
                ("project_id", "in", projects.ids),
                ("task_id", "!=", False),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("validated", "=", False),
            ], order="employee_id, date asc")

            emp_groups = {}
            for line in lines:
                emp_id = line.employee_id.id
                if emp_id not in emp_groups:
                    emp_groups[emp_id] = {
                        "employee": line.employee_id,
                        "lines": [],
                        "total_days": 0.0,
                    }
                emp_groups[emp_id]["lines"].append(line)
                emp_groups[emp_id]["total_days"] += line.unit_amount / 8.0

            groups = list(emp_groups.values())

        prev_month = sel_month - 1 if sel_month > 1 else 12
        prev_year = sel_year if sel_month > 1 else sel_year - 1
        next_month = sel_month + 1 if sel_month < 12 else 1
        next_year = sel_year if sel_month < 12 else sel_year + 1

        return request.render("achmitech_portal_timesheets.portal_client_timesheets", {
            "groups": groups,
            "no_access": not bool(projects),
            "sel_month": sel_month,
            "sel_year": sel_year,
            "month_name": MONTH_NAMES_FR[sel_month],
            "prev_month": prev_month,
            "prev_year": prev_year,
            "next_month": next_month,
            "next_year": next_year,
        })

    @http.route("/my/client-timesheets/validate", type="http", auth="user", website=True, methods=["POST"])
    def portal_client_timesheet_validate(self, **post):
        """Bulk-validate all unvalidated lines for one employee in the given month."""
        projects = self._get_client_projects()
        if not projects:
            return request.redirect("/my/client-timesheets")

        try:
            employee_id = int(post.get("employee_id") or 0)
            sel_year = int(post.get("year") or 0)
            sel_month = int(post.get("month") or 0)
        except (ValueError, TypeError):
            return request.redirect("/my/client-timesheets")

        if not (employee_id and sel_year and sel_month):
            return request.redirect("/my/client-timesheets")

        from datetime import date as dt_date
        date_from = dt_date(sel_year, sel_month, 1)
        date_to = dt_date(sel_year, sel_month, cal_module.monthrange(sel_year, sel_month)[1])

        lines = request.env["account.analytic.line"].sudo().search([
            ("employee_id", "=", employee_id),
            ("project_id", "in", projects.ids),
            ("task_id", "!=", False),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("validated", "=", False),
        ])
        # Use _write() to bypass timesheet_grid._check_can_write, which blocks
        # validated=True without env.su respect. Our module loads before timesheet_grid
        # alphabetically so MRO overrides don't help here.
        lines._write({"validated": True, "correction_requested": False})
        # Keep timesheet_grid's last validated date tracking in sync (if installed).
        if hasattr(lines, "_update_last_validated_timesheet_date"):
            lines._update_last_validated_timesheet_date()

        request.session["client_ts_flash"] = {
            "type": "success",
            "message": "Les feuilles de temps ont été validées avec succès. Cette action est irréversible.",
        }
        return request.redirect(f"/my/client-timesheets?month={sel_month}&year={sel_year}")

    @http.route("/my/client-timesheets/validate-line/<int:line_id>", type="http", auth="user", website=True, methods=["POST"])
    def portal_client_timesheet_validate_line(self, line_id, **post):
        """Validate a single timesheet line."""
        projects = self._get_client_projects()
        if not projects:
            return request.redirect("/my/client-timesheets")

        line = request.env["account.analytic.line"].sudo().search([
            ("id", "=", line_id),
            ("project_id", "in", projects.ids),
            ("validated", "=", False),
        ], limit=1)

        sel_month = sel_year = None
        if line:
            sel_month, sel_year = line.date.month, line.date.year
            line._write({"validated": True, "correction_requested": False})
            if hasattr(line, "_update_last_validated_timesheet_date"):
                line._update_last_validated_timesheet_date()
            request.session["client_ts_flash"] = {
                "type": "success",
                "message": f"La saisie du {line.date.strftime('%d/%m/%Y')} ({line.employee_id.name}) a été validée.",
            }
        else:
            try:
                sel_month = int(post.get("month") or 0) or None
                sel_year = int(post.get("year") or 0) or None
            except (ValueError, TypeError):
                pass

        redirect = f"/my/client-timesheets?month={sel_month}&year={sel_year}" if sel_month else "/my/client-timesheets"
        return request.redirect(redirect)

    @http.route("/my/client-timesheets/refuse/<int:line_id>", type="http", auth="user", website=True, methods=["POST"])
    def portal_client_timesheet_refuse(self, line_id, **post):
        """Refuse a single line: post a message on the task, keep the line editable."""
        projects = self._get_client_projects()
        if not projects:
            return request.redirect("/my/client-timesheets")

        line = request.env["account.analytic.line"].sudo().search([
            ("id", "=", line_id),
            ("project_id", "in", projects.ids),
            ("validated", "=", False),
        ], limit=1)

        sel_month = sel_year = None
        if line:
            sel_month, sel_year = line.date.month, line.date.year
            reason = (post.get("reason") or "").strip()

            # Format date as dd/mm/yyyy
            date_display = line.date.strftime("%d/%m/%Y")
            day_value = line.unit_amount / 8.0
            day_display = f"{day_value:g}j"

            body_parts = [
                Markup("Le client demande une correction pour la saisie du <strong>{}</strong> ({}).").format(date_display, day_display),
            ]
            if line.name:
                body_parts.append(Markup("Description : <em>{}</em>").format(escape(line.name)))
            if reason:
                body_parts.append(Markup("Remarques : <em>{}</em>").format(escape(reason)))
            body_parts.append(Markup("Veuillez corriger et resoumettre cette saisie."))

            body = Markup("<br/>").join(body_parts)

            line._write({"correction_requested": True})
            line.task_id.sudo().message_post(
                body=body,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            request.session["client_ts_flash"] = {
                "type": "warning",
                "message": f"Une demande de correction a été envoyée pour la saisie du {date_display} ({line.employee_id.name}).",
            }

        redirect = f"/my/client-timesheets?month={sel_month}&year={sel_year}" if sel_month else "/my/client-timesheets"
        return request.redirect(redirect)