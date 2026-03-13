# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_ma_phone_allowance = fields.Monetary(
        readonly=False,
        related="version_id.l10n_ma_phone_allowance",
        inherited=True,
        groups="hr_payroll.group_hr_payroll_user",
    )
