# -*- coding: utf-8 -*-

import secrets
from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)
class HrCandidate(models.Model):
    _inherit = "hr.candidate"

    evaluation_ids = fields.One2many(
        comodel_name="hr.applicant.evaluation",
        inverse_name="candidate_id",
        string="Évaluations",
    )

    access_token = fields.Char(readonly=True, copy=False)
    dossier_state = fields.Selection([
        ("draft", "Draft"),
        ("submitted", "Submitted"),
    ], default="draft")
    dossier_submitted_at = fields.Datetime()

    def action_generate_dossier_token(self):
        """Generate token if missing (safe)."""
        for rec in self:
            if not rec.access_token:
                rec.access_token = secrets.token_urlsafe(32)
                _logger.info("XXXXXXXXXXX %s", rec.access_token)
        return True