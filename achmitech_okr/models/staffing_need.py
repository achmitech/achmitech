# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class StaffingNeed(models.Model):
    _name = "staffing.need"
    _description = "Besoin en personnel"
    _order = "state, name"

    name = fields.Char(required=True)
    staffing_plan_id = fields.Many2one("staffing.plan", required=True, ondelete="cascade")
    company_id = fields.Many2one("res.company", related='staffing_plan_id.company_id', string='Company', store=True, readonly=True)
    assigned_to = fields.Many2one("res.users", string="Assigné à")
    assigned_date = fields.Datetime(string="Date d'affectation")
    number_of_positions = fields.Integer(string="Nombre de postes", required=True)
    job_id = fields.Many2one("hr.job", string="Poste")
    applicant_ids = fields.One2many("hr.applicant", "staffing_need_id", string="Candidats")

    positions_filled = fields.Integer(
        string="Postes pourvus",
        compute="_compute_positions_filled",
        store=True,
    )

    state = fields.Selection([
        ("draft", "Brouillon"),
        ("assigned", "Affecté"),
        ("closed", "Clôturé"),
    ], default="draft", string="Statut")

    @api.depends("applicant_ids.stage_id")
    def _compute_positions_filled(self):
        for need in self:
            need.positions_filled = sum(
                1 for app in need.applicant_ids if app.stage_id.hired_stage
            )

    @api.constrains("number_of_positions")
    def _check_positions(self):
        for rec in self:
            if rec.number_of_positions < 1:
                raise ValidationError(_("Le nombre de postes doit être >= 1."))

    def action_assign(self):
        for rec in self:
            rec.state = "assigned"
            if not rec.assigned_date:
                rec.assigned_date = fields.Datetime.now()

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset_draft(self):
        self.write({"state": "draft"})
