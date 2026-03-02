# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.addons.achmitech_okr.models.okr_recontact_log import OUTCOME_SELECTION


class OkrRecontactWizard(models.TransientModel):
    _name = "okr.recontact.wizard"
    _description = "Assistant de recontact vivier"

    applicant_id = fields.Many2one("hr.applicant", required=True)
    date = fields.Date(
        string="Date du contact", default=fields.Date.context_today
    )
    outcome = fields.Selection(OUTCOME_SELECTION, string="Résultat")
    note = fields.Text(string="Notes")
    referral_name = fields.Char(string="Nom du recommandé")
    referral_contact = fields.Char(string="Contact du recommandé")
    next_contact_date = fields.Date(string="Prochain contact")

    def action_confirm(self):
        self.ensure_one()
        self.env["okr.recontact.log"].create({
            "applicant_id": self.applicant_id.id,
            "partner_id": self.applicant_id.partner_id.id or False,
            "date": self.date,
            "user_id": self.env.uid,
            "outcome": self.outcome,
            "note": self.note or False,
            "referral_name": self.referral_name or False,
            "referral_contact": self.referral_contact or False,
            "next_contact_date": self.next_contact_date or False,
        })
        return {"type": "ir.actions.act_window_close"}
