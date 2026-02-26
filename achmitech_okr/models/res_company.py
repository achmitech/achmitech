# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    okr_success_points_threshold = fields.Float(
        string="OKR Success Points Threshold",
        store=True,
        default=0.7,
    )

