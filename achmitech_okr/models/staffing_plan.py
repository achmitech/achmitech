# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class StaffingPlan(models.Model):
    _name = "staffing.plan"
    _description = "Staffing Plan"
    _order = "date_from desc, name"

    name = fields.Char('Staffing Plan Name', required=True, index='trigram', copy=False, default='New')
    company_id = fields.Many2one('res.company', 'Societé', required=True, index=True, default=lambda self: self.env.company.id)
    department_id = fields.Many2one("hr.department", required=True)
    staffing_need_ids = fields.One2many("staffing.need", "staffing_plan_id", string="Besoins en personnel")
    date_from = fields.Date("Date de début", required=True)
    date_to = fields.Date("Date de fin", required=True)

    presented_sum = fields.Integer(
        string="Nb candidats présentés (total)",
        compute="_compute_client_interview_kpis",
        store=True,
    )
    client_interview_passed_sum = fields.Integer(
        string="Nb EC terminé (total)",
        compute="_compute_client_interview_kpis",
        store=True,
    )
    client_interview_pass_rate = fields.Float(
        string="Taux EC terminé / présentés",
        compute="_compute_client_interview_kpis",
        store=True,
    )

    @api.depends(
        "date_from", "date_to",
        "staffing_need_ids",
        "staffing_need_ids.applicant_ids.presented_to_client_date",
        "staffing_need_ids.applicant_ids.client_interview_status",
    )
    def _compute_client_interview_kpis(self):
        Applicant = self.env["hr.applicant"].sudo()
        for plan in self:
            plan.presented_sum = 0
            plan.client_interview_passed_sum = 0
            plan.client_interview_pass_rate = 0.0

            if not plan.staffing_need_ids:
                continue

            domain = [
                ("company_id", "=", plan.company_id.id),
                ("staffing_need_id", "in", plan.staffing_need_ids.ids),
                ("presented_to_client_date", "!=", False),
            ]

            # Match plan period (recommended)
            if plan.date_from:
                domain.append(("presented_to_client_date", ">=", plan.date_from))
            if plan.date_to:
                domain.append(("presented_to_client_date", "<=", plan.date_to))

            presented = Applicant.search_count(domain)
            passed = Applicant.search_count(domain + [("client_interview_status", "=", "passed")])

            plan.presented_sum = presented
            plan.client_interview_passed_sum = passed
            plan.client_interview_pass_rate = (passed / presented) if presented else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("staffing.plan") or _("New")
        return super().create(vals_list)