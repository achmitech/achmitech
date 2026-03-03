# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StaffingNeed(models.Model):
    _name = "staffing.need"
    _description = "Besoin en personnel"
    _order = "state, urgency, name"

    staffing_plan_id = fields.Many2one("staffing.plan", required=True, ondelete="cascade")
    company_id = fields.Many2one("res.company", related='staffing_plan_id.company_id', string='Company', store=True, readonly=True)

    name = fields.Char(string="Poste", required=True)
    partner_id = fields.Many2one("res.partner", string="Client")
    technology = fields.Char(string="Technologie clé")
    seniority_min = fields.Integer(string="Séniorité min. (ans)")
    urgency = fields.Selection([
        ("1", "Urgente"),
        ("2", "Normale"),
        ("3", "Basse"),
    ], string="Urgence", default="2")

    date_opened = fields.Date(string="Date d'ouverture")
    assigned_to = fields.Many2one("res.users", string="Assigné à")
    assigned_date = fields.Datetime(string="Date d'affectation")
    number_of_positions = fields.Integer(string="Nombre de postes", required=True)
    margin_rate = fields.Float(string="Taux de marge (%)", digits=(5, 2))

    applicant_ids = fields.One2many("hr.applicant", "staffing_need_id", string="Candidats")

    positions_filled = fields.Integer(
        string="Placement",
        compute="_compute_positions_filled",
        store=True,
    )
    cv_sent_count = fields.Integer(
        string="CV envoyés",
        compute="_compute_pipeline_counts",
        store=True,
    )
    client_interview_count = fields.Integer(
        string="Entretiens clients",
        compute="_compute_pipeline_counts",
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

    @api.depends("applicant_ids", "applicant_ids.presented_to_client_date", "applicant_ids.client_interview_status")
    def _compute_pipeline_counts(self):
        for need in self:
            need.cv_sent_count = len(need.applicant_ids)
            need.client_interview_count = sum(
                1 for app in need.applicant_ids if app.presented_to_client_date
            )

    @api.constrains("number_of_positions")
    def _check_positions(self):
        for rec in self:
            if rec.number_of_positions < 1:
                raise ValidationError(_("Le nombre de postes doit être >= 1."))

    @api.constrains("seniority_min")
    def _check_seniority_min(self):
        for rec in self:
            if rec.seniority_min < 0:
                raise ValidationError(_("La séniorité minimale doit être un nombre positif."))

    def action_assign(self):
        for rec in self:
            rec.state = "assigned"
            if not rec.assigned_date:
                rec.assigned_date = fields.Datetime.now()

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset_draft(self):
        self.write({"state": "draft"})
