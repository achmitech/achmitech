# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    okr_success_points_threshold = fields.Float(
        string="OKR Success Points Threshold",
        related="company_id.okr_success_points_threshold",
        readonly=False,
    )