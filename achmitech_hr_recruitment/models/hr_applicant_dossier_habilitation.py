from odoo import fields, models

class HrApplicantDossierHabilitation(models.Model):
    _name = "hr.applicant.dossier.habilitation"
    _description = "Dossier – Habilitation"
    _order = "sequence, id"

    applicant_id = fields.Many2one(
        "hr.applicant",
        string="Candidat",
        required=True,
        ondelete="cascade",
        index=True,
    )

    sequence = fields.Integer(default=10)

    title = fields.Char(
        string="Habilitation / Certification",
        required=True,
    )
