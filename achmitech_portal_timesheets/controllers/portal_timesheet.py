# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class PortalTimesheet(CustomerPortal):

    def _get_employee_for_portal_user(self):
        # Standard mapping: portal user -> employee via hr.employee.user_id,
        # scoped to the current company to avoid cross-company matches in multi-company setups.
        return request.env["hr.employee"].sudo().search(
            [
                ("user_id", "=", request.env.user.id),
                ("company_id", "=", request.env.company.id),
            ],
            limit=1
        )

    def _task_redirect(self, task):
        url = task.get_portal_url()  # may contain ?access_token=...
        return request.redirect(url + "#task_timesheets")

    def _is_task_locked(self, task):
        return bool(task.stage_id and task.stage_id.fold)

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

        # Convert day ratio to hours (8h/day)
        unit_amount = ratio * 8.0

        # Validate date early — before any ORM call that uses it
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

        # Authorization checks: apply to both new entries and updates
        if request.env.user not in task.user_ids:
            request.session["ts_flash"] = {"type": "danger", "message": "Vous n'êtes pas assigné(e) à cette tâche."}
            return self._task_redirect(task)

        if task.stage_id and task.stage_id.fold:
            request.session["ts_flash"] = {
                "type": "danger",
                "message": "Cette tâche est clôturée. Vous ne pouvez plus modifier vos feuilles de temps."
            }
            return self._task_redirect(task)

        # One entry per day per task (per employee) — update if exists, create otherwise
        existing = request.env["account.analytic.line"].sudo().search([
            ("employee_id", "=", employee.id),
            ("date", "=", parsed_date),
            ("task_id", "=", task.id),
            ("company_id", "=", request.env.company.id),
        ], limit=1)

        if existing:
            existing.write({
                "name": description,
                "unit_amount": unit_amount,
                "project_id": project.id,
                "task_id": task.id,
            })
            request.session["ts_flash"] = {"type": "success", "message": "Votre saisie pour cette date a été mise à jour."}
            return self._task_redirect(task)

        # Create timesheet using sudo to bypass ACL
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
