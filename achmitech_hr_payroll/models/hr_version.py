# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api
class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_ma_phone_allowance = fields.Monetary(string="Téléphone / Internet")
    sign_wage_annual_gross = fields.Char(compute='_compute_sign_wage_annual_gross')
    sign_wage_annual_gross_words = fields.Char(compute='_compute_sign_wage_annual_gross')

    @api.depends(
        'wage',
        'l10n_ma_transport_exemption',
        'l10n_ma_phone_allowance',
        'l10n_ma_meal_allowance',
        'l10n_ma_kilometric_exemption',
    )
    def _compute_sign_wage_annual_gross(self):
        for version in self:
            monthly = (
                (version.wage or 0)
                + (version.l10n_ma_transport_exemption or 0)
                + (version.l10n_ma_phone_allowance or 0)
                + (version.l10n_ma_meal_allowance or 0)
                + (version.l10n_ma_kilometric_exemption or 0)
            )
            annual = monthly * 12
            # French number format: narrow-space thousands separator, comma decimal
            formatted = f"{annual:,.2f}".replace(',', '\u202f').replace('.', ',')
            version.sign_wage_annual_gross = f"{formatted} MAD"
            version.sign_wage_annual_gross_words = num2words(int(annual), lang='fr') + ' dirhams'
    client_id = fields.Many2one(
        'res.partner',
        related='originated_offer_id.client_id',
        store=True, readonly=False,
        string="Client",
    )
    mission_order_ref = fields.Char(
        related='originated_offer_id.mission_order_ref',
        store=True, readonly=False,
        string="Référence ordre de mission",
    )

    def _get_whitelist_fields_from_template(self):
        fields = super()._get_whitelist_fields_from_template()
        if self.env.company.country_id.code == 'MA':
            fields += ['l10n_ma_phone_allowance']
        return fields
