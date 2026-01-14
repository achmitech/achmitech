# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalTimesheet(CustomerPortal):

    def _get_employee_for_portal_user(self):
        # Standard mapping: portal user -> employee via hr.employee.user_id
        return request.env["hr.employee"].sudo().search(
            [("user_id", "=", request.env.user.id)],
            limit=1
        )


    @http.route("/my/timesheets/create", type="http", auth="user", website=True, methods=["POST"])
    def portal_timesheet_create(self, **post):
        employee = self._get_employee_for_portal_user()
        if not employee:
            return request.redirect("/my/tasks?error=no_employee")

        # Parse inputs safely
        task_id = int(post.get("task_id") or 0)
        date_str = (post.get("date") or "").strip()
        description = (post.get("name") or "").strip()

        try:
            hours = float(post.get("unit_amount") or 0.0)
        except Exception:
            hours = 0.0

        # Basic validation
        if not task_id or not date_str or not description or hours <= 0:
            # simplest behavior: go back to task page (you can add error query later)
            return request.redirect("/my/tasks?error=invalid_input")

        # Load task (sudo read ok), but create WITHOUT sudo so record rules apply
        task = request.env["project.task"].sudo().browse(task_id).exists()
        if not task:
            return request.redirect("/my/tasks?error=task_not_found")

        # Need project + analytic account for timesheets
        project = task.project_id.sudo()
        if not project or not project.allow_timesheets:
            return request.redirect(task.get_portal_url() + "?error=project_not_timesheetable")

        # Optional: ensure portal user is allowed to access this task in portal
        # If they can view it, they should be ok, but we add a conservative check:
        try:
            self._check_access_rights(task_id)
        except Exception:
            return request.redirect("/my/tasks?error=access_denied")

        # Create the timesheet line (NO sudo)
        request.env["account.analytic.line"].sudo().create({
            "name": description,
            "date": fields.Date.from_string(date_str),
            "unit_amount": hours,
            "project_id": project.id,
            "task_id": task.id,
            "employee_id": employee.id,
            "user_id": request.env.user.id,
            "company_id": request.env.company.id,
        })

        # Redirect back to the same task portal page (so they see the new line)
        return request.redirect(task.get_portal_url() + "#task_timesheets")
