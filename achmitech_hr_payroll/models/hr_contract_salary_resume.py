# -*- coding: utf-8 -*-
from odoo import fields, models


class HrContractSalaryResume(models.Model):
    _inherit = 'hr.contract.salary.resume'

    def _get_available_fields(self):
        result = super()._get_available_fields()
        extra = [
            ('E_CNSS', 'CNSS Salariale'),
            ('E_AMO', 'AMO Salariale'),
            ('NET_INCOME_TAX', 'IR'),
            ('CIMR', 'CIMR'),
            ('PRO_CONTRIBUTION', 'Contribution Professionnelle'),
        ]
        existing = {code for code, _ in result}
        return result + [(c, n) for c, n in extra if c not in existing]

    code = fields.Selection(_get_available_fields)
    hide_if_zero = fields.Boolean(string="Masquer si zéro", default=False)
