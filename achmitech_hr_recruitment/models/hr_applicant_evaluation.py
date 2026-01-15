# models/hr_applicant_evaluation.py
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class HrApplicantEvaluation(models.Model):
    _name = "hr.applicant.evaluation"
    _description = "Applicant Evaluation"
    _order = "create_date"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # pratique pour audit/trace

    applicant_id = fields.Many2one(
        string="Candidature",
        comodel_name="hr.applicant",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    candidate_id = fields.Many2one(
        comodel_name="hr.candidate",
        string="Candidat",
        related="applicant_id.candidate_id",
        store=True,
        index=True,
        readonly=True,
    )
    job_id = fields.Many2one(
        string="Poste",
        comodel_name="hr.job",
        related="applicant_id.job_id",
        store=True,
        readonly=True,
    )

    date = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)

    stage_id = fields.Many2one(
        string="Etape d'entretien",
        comodel_name="hr.recruitment.stage",
        tracking=True,
    )

    interviewer_id = fields.Many2one(
        string="Interviewer",
        comodel_name="res.users",
        default=lambda self: self.env.user,
        tracking=True,
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

    decision = fields.Selection(
        string="Décision",
        selection=[
            ("proceed", "Poursuivre"),
            ("hold", "En attente"),
            ("reject", "Rejeter"),
            ("candidate_withdrew", "Candidat retiré"),
        ],
        required=True,
        default="proceed",
        tracking=True,
    )

    comment = fields.Text("Commentaires", tracking=True)

    @api.constrains("decision", "rejection_reason_id")
    def _check_reason_required(self):
        for rec in self:
            if rec.decision in ("reject", "candidate_withdrew") and not rec.comment:
                raise ValidationError("Un commentaire est requis lorsque la décision est Rejetée ou que le candidat s'est retiré.")

    @api.onchange("applicant_id")
    def _onchange_applicant_id(self):
        for rec in self:
            if rec.applicant_id and not rec.stage_id:
                rec.stage_id = rec.applicant_id.stage_id
