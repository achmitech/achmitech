# -*- coding: utf-8 -*-
from odoo import fields, models

SENIORITY_SELECTION = [
    ("intern", "Stagiaire"),
    ("junior", "Junior"),
    ("mid", "Confirmé"),
    ("senior", "Senior"),
]


class HrJob(models.Model):
    _inherit = "hr.job"

    seniority_level = fields.Selection(
        SENIORITY_SELECTION,
        string="Niveau",
    )
