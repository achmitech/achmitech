# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    correction_requested = fields.Boolean(
        string="Correction demandée",
        default=False,
        help="Le client a demandé une correction sur cette saisie.",
    )

    def write(self, vals):
        # When the employee edits the line (amount, date, description),
        # clear the correction flag so the client knows it was addressed.
        employee_fields = {"unit_amount", "date", "name"}
        if employee_fields & vals.keys():
            vals = dict(vals, correction_requested=False)
        return super().write(vals)
