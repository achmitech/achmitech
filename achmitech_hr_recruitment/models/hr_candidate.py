# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrCandidate(models.Model):
    _inherit = "hr.candidate"

    evaluation_ids = fields.One2many(
        comodel_name="hr.applicant.evaluation",
        inverse_name="candidate_id",
        string="Évaluations",
    )