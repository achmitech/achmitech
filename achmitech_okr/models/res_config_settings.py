# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    okr_success_points_threshold = fields.Float(
        string="OKR Success Points Threshold",
        help="The standard value for evaluate OKR successful or failed",
        default=0.70,
        config_parameter="achmitech_okr.okr_success_points_threshold",
    )
