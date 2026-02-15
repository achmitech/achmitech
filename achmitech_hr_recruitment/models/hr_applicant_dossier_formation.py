from odoo import fields, models

class HrApplicantDossierFormation(models.Model):
    _name = "hr.applicant.dossier.formation"
    _description = "Dossier – Formation"
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
        string="Intitulé",
        required=True,
    )

    start = fields.Date(string="Date début")
    end = fields.Date(string="Date fin")
