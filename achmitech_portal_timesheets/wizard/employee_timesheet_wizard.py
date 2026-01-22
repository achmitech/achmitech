# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class EmployeeTimesheetWizard(models.TransientModel):
    _name = "employee.timesheet.wizard"
    _description = "Assistant - CRA client (feuille de temps)"

    employee_id = fields.Many2one("hr.employee", string="Employé")

    project_id = fields.Many2one(
        "project.project",
        string="Projet client",
        required=True,
    )

    allowed_task_ids = fields.Many2many(
        "project.task",
        compute="_compute_allowed_task_ids",
        string="Tâches autorisées",
    )

    task_id = fields.Many2one(
        "project.task",
        string="Tâche du projet",
        domain="[('id', 'in', allowed_task_ids)]",
    )

    @api.depends("project_id", "employee_id")
    def _compute_allowed_task_ids(self):
        Task = self.env["project.task"].sudo()
        for rec in self:
            rec.allowed_task_ids = False

            # no project OR no employee
            if not rec.project_id or not rec.employee_id:
                continue

            user = rec.employee_id.user_id

            # no linked user ⇒ NO TASKS
            if not user:
                continue

            # Only tasks of the project AND assigned to the user
            tasks = Task.search([
                ("project_id", "=", rec.project_id.id),
                ("user_ids", "in", user.id),
            ])

            rec.allowed_task_ids = tasks

    @api.onchange("project_id")
    def _onchange_project_id(self):
        self.task_id = False
    
    
    date_from = fields.Date(string="Du", required=True)
    date_to = fields.Date(string="Au", required=True)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for w in self:
            if w.date_from and w.date_to and w.date_from > w.date_to:
                raise ValidationError("La date 'Du' doit être antérieure à la date 'Au'.")

            # optional: limit to <= 31 days (keep if you want)
            if w.date_from and w.date_to and (w.date_to - w.date_from).days > 31:
                raise ValidationError("La période ne doit pas dépasser 31 jours.")
    
    def action_print_report(self):
        self.ensure_one()

        data = {
            "employee_id": self.employee_id.id,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "project_id": self.project_id.id,
            "task_id": self.task_id.id,
        }

        return self.env.ref(
            "achmitech_portal_timesheets.timesheet_report_interim"
        ).report_action(self, data=data)
    
    def _get_report_base_filename(self):
        self.ensure_one()
        return f"CRA_{self.project_id.name}_{self.employee_id.name}_Du_{self.date_from}_Au_{self.date_to}"