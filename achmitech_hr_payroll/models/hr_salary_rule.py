# -*- coding: utf-8 -*-
from odoo import models, fields


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    l10n_ma_rubric_number = fields.Char(string="N° Rubrique")