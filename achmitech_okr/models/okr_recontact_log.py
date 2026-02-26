# -*- coding: utf-8 -*-
from odoo import fields, models

OUTCOME_SELECTION = [
    ("interested", "Toujours intéressé"),
    ("not_interested", "Pas intéressé pour l'instant"),
    ("no_answer", "Pas de réponse"),
    ("referral", "A donné une recommandation"),
    ("callback", "Rappel à prévoir"),
]


class OkrRecontactLog(models.Model):
    _name = "okr.recontact.log"
    _description = "Journal de recontact vivier"
    _order = "date desc, id desc"

    applicant_id = fields.Many2one(
        "hr.applicant", required=True, ondelete="cascade", index=True
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    user_id = fields.Many2one(
        "res.users", string="Recruteur", default=lambda self: self.env.user
    )
    outcome = fields.Selection(OUTCOME_SELECTION, string="Résultat", required=True)
    note = fields.Text(string="Notes")
    referral_name = fields.Char(string="Nom du recommandé")
    referral_contact = fields.Char(string="Contact du recommandé")
    next_contact_date = fields.Date(string="Prochain contact")
