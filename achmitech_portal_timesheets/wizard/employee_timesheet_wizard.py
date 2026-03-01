# -*- coding: utf-8 -*-

import calendar
from datetime import date

from odoo import models, fields, api

class EmployeeTimesheetWizard(models.TransientModel):
    _name = "employee.timesheet.wizard"
    _description = "Assistant - CRA client (feuille de temps)"

    company_id = fields.Many2one(
        "res.company",
        string="Société",
        default=lambda self: self.env.company,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employé",
        domain="[('company_id', '=', company_id)]",
    )

    project_id = fields.Many2one(
        "project.project",
        string="Projet client",
        required=True,
        domain="[('company_id', '=', company_id)]",
    )

    allowed_task_ids = fields.Many2many(
        "project.task",
        compute="_compute_allowed_task_ids",
        string="Tâches autorisées",
    )

    task_id = fields.Many2one(
        "project.task",
        string="Tâche du projet",
        required=True,
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
    
    
    period_month = fields.Selection(
        selection=[
            ('1', 'Janvier'), ('2', 'Février'), ('3', 'Mars'), ('4', 'Avril'),
            ('5', 'Mai'), ('6', 'Juin'), ('7', 'Juillet'), ('8', 'Août'),
            ('9', 'Septembre'), ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre'),
        ],
        string="Mois",
        required=True,
        default=lambda self: str(fields.Date.today().month),
    )

    period_year = fields.Integer(
        string="Année",
        required=True,
        default=lambda self: fields.Date.today().year,
    )

    def action_print_report(self):
        self.ensure_one()

        month = int(self.period_month)
        year = self.period_year
        date_from = fields.Date.to_string(date(year, month, 1))
        date_to = fields.Date.to_string(date(year, month, calendar.monthrange(year, month)[1]))

        data = {
            "employee_id": self.employee_id.id,
            "date_from": date_from,
            "date_to": date_to,
            "project_id": self.project_id.id,
            "task_id": self.task_id.id,
        }

        return self.env.ref(
            "achmitech_portal_timesheets.timesheet_report_interim"
        ).report_action(self, data=data)

    def _get_report_base_filename(self):
        self.ensure_one()
        month_names_fr = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                          'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        return f"CRA_{self.project_id.name}_{self.employee_id.name}_{month_names_fr[int(self.period_month)]}_{self.period_year}"