# -*- coding: utf-8 -*-

from odoo import fields, models

class HrRecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"

    is_client_interview = fields.Boolean(string="Etape reservée au client ?")