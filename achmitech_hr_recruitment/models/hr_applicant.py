# -*- coding: utf-8 -*-

import secrets
from odoo import models, fields, api


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    evaluation_ids = fields.One2many(
        comodel_name="hr.applicant.evaluation",
        inverse_name="applicant_id",
        string="Evaluations",
        copy=False,
    )

    dca_access_token = fields.Char(copy=False, index=True)
    dca_submitted = fields.Boolean(string="Dossier soumis", default=False, tracking=True)
    dca_submitted_date = fields.Datetime(string="Date de soumission", tracking=True)

    # optional but VERY useful for debugging / audit
    dca_payload_json = fields.Text(string="Snapshot dossier (JSON)")

    dossier_experience_ids = fields.One2many(
        "hr.applicant.dossier.experience",
        "applicant_id",
        string="Expériences (Dossier)",
        copy=False,
    )
    def _regenerate_dca_token(self):
        for rec in self:
            if not rec.dca_access_token:
                rec.dca_access_token = secrets.token_urlsafe(32)
                rec.dca_submitted = False

