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

    def _task_redirect(self, task):
        url = task.get_portal_url()  # may contain ?access_token=...
        return request.redirect(url + "#task_timesheets")


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
            time_str = (post.get("time_spent") or "").strip()  # "02:35"
            hours, minutes = time_str.split(":")
            unit_amount = int(hours) + int(minutes) / 60.0
        except Exception:
            request.session["ts_flash"] = {"type": "danger", "message": "Format de durée invalide."}
            return self._task_redirect(task)

        if not date_str or unit_amount <= 0:
            request.session["ts_flash"] = {"type": "danger", "message": "Veuillez saisir une date et une durée valide."}
            return self._task_redirect(task)

        project = task.project_id.sudo()
        if not project or not project.allow_timesheets:
            request.session["ts_flash"] = {"type": "danger", "message": "Cette tâche appartient à un projet qui n'autorise pas la saisie des feuilles de temps."}
            return self._task_redirect(task)

        if request.env.user not in task.user_ids:
            request.session["ts_flash"] = {"type": "danger", "message": "Vous n'êtes pas assigné(e) à cette tâche."}
            return self._task_redirect(task)

        # Create timesheet
        # NOTE: You're using sudo() here (comment said otherwise). Keep sudo only if portal user lacks rights,
        # but ensure your checks above are strict (they are).
        request.env["account.analytic.line"].sudo().create({
            "name": description,
            "date": fields.Date.from_string(date_str),
            "unit_amount": unit_amount,
            "project_id": project.id,
            "task_id": task.id,
            "employee_id": employee.id,
            "user_id": request.env.user.id,
            "company_id": request.env.company.id,
        })

        request.session["ts_flash"] = {"type": "success", "message": "Votre temps a été enregistré avec succès."}
        return self._task_redirect(task)
