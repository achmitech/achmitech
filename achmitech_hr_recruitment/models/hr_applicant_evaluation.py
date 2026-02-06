# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class HrApplicantEvaluation(models.Model):
    _name = "hr.applicant.evaluation"
    _description = "Applicant Evaluation"
    _order = "create_date"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # pratique pour audit/trace

    applicant_id = fields.Many2one(
        string="Candidat",
        comodel_name="hr.applicant",
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        related="applicant_id.partner_id",
        store=True,
        index=True,
    )
    job_id = fields.Many2one(
        string="Poste",
        comodel_name="hr.job",
        related="applicant_id.job_id",
        store=True,
        index=True,
    )

    date = fields.Datetime(default=fields.Datetime.now)

    stage_id = fields.Many2one(
        string="Etape d'entretien",
        comodel_name="hr.recruitment.stage",
        tracking=True,
    )

    interviewer_id = fields.Many2one(
        string="Interviewer",
        comodel_name="res.users",
        default=lambda self: self.env.user,
    )

    rating = fields.Selection(
        string="Score",
        selection=[
            ("5", "Très défavorable"),
            ("4", "Défavorable"),
            ("3", "À évaluer"),
            ("2", "Favorable"),
            ("1", "Très favorable"),
        ],
        tracking=True,
    )

    decision_state = fields.Selection(
        selection=[("normal", "Normal"), ("done", "Done"), ("blocked", "Blocked")],
        string="Décision (clé)"
    )

    decision = fields.Char(
        string="Décision"
    )

    comment = fields.Text("Commentaires")

    def _get_decision_label(self, stage, state):
        if state == "done":
            return stage.legend_done or "Prêt pour l'étape suivante"
        if state == "blocked":
            return stage.legend_blocked or "Bloqué"
        return stage.legend_normal or "En cours"

    def _snapshot_decision(self):
        for rec in self:
            applicant = rec.applicant_id
            if not applicant:
                continue
            stage = rec.stage_id or applicant.stage_id
            state = applicant.kanban_state or "normal"
            rec.decision_state = state
            rec.decision = rec._get_decision_label(stage, state)


    @api.constrains("decision_state", "comment")
    def _check_reason_required(self):
        for rec in self:
            if rec.decision_state == "blocked" and not rec.comment:
                raise ValidationError("Un commentaire est requis lorsque la décision est Bloqué.")


    @api.onchange("applicant_id", "stage_id")
    def _onchange_applicant_id(self):
        for rec in self:
            if not rec.applicant_id:
                rec.stage_id = False
                rec.decision = False
                rec.decision_state = False
                continue

            if not rec.stage_id:
                rec.stage_id = rec.applicant_id.stage_id

            # Preview only if empty
            if not rec.decision:
                stage = rec.stage_id or rec.applicant_id.stage_id
                state = rec.applicant_id.kanban_state or "normal"
                rec.decision_state = state
                rec.decision = rec._get_decision_label(stage, state)


    @api.constrains("stage_id", "interviewer_id")
    def _check_interviewer_required(self):
        for rec in self:
            if rec.stage_id and not rec.stage_id.is_client_interview and not rec.interviewer_id:
                raise ValidationError("L'interviewer est obligatoire sauf pour une étape 'Entretien client (EC)'.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._snapshot_decision()
        return records
