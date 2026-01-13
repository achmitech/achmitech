# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    evaluation_ids = fields.One2many(
        comodel_name="hr.applicant.evaluation",
        inverse_name="applicant_id",
        string="Evaluations",
        copy=False,
    )

