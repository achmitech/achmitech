# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api
from odoo.addons.hr_contract_salary.utils.hr_version import requires_hr_version_context

class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_ma_phone_allowance = fields.Monetary(string="Téléphone / Internet")
    sign_wage_annual_gross = fields.Char(compute='_compute_sign_wage_annual_gross')
    sign_wage_annual_gross_words = fields.Char(compute='_compute_sign_wage_annual_gross')

    @api.depends('originated_offer_id.final_yearly_costs')
    def _compute_sign_wage_annual_gross(self):
        for version in self:
            annual = version.originated_offer_id.final_yearly_costs or 0
            version.sign_wage_annual_gross = f"{annual:,.2f} MAD".replace(',', '\u202f')
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



class HrContractSalaryOffer(models.Model):
    _inherit = 'hr.contract.salary.offer'

    client_id = fields.Many2one('res.partner', string="Client")
    mission_order_ref = fields.Char(string="Référence ordre de mission")

    l10n_ma_meal_allowance = fields.Monetary(string="Panier repas")
    l10n_ma_transport_exemption = fields.Monetary(string="Transport")
    l10n_ma_kilometric_exemption = fields.Monetary(string="Indemnité kilométrique")
    l10n_ma_phone_allowance = fields.Monetary(string="Téléphone / Internet")

    _INDEMNITY_FIELDS = [
        'l10n_ma_meal_allowance',
        'l10n_ma_transport_exemption',
        'l10n_ma_kilometric_exemption',
        'l10n_ma_phone_allowance',
    ]

    cnss_sal_wage = fields.Monetary(compute='_compute_salary', store=True, string="CNSS Salariale")
    amo_sal_wage = fields.Monetary(compute='_compute_salary', store=True, string="AMO Salariale")
    ir_wage = fields.Monetary(compute='_compute_salary', store=True, string="IR")

    def write(self, vals):
        # Adjust FYC by the indemnity delta so the base simulation keeps the correct gross.
        # Indemnities are non-cotisable: employer pays them on top, no social contributions apply.
        fyc_updates = {}
        if any(f in vals for f in self._INDEMNITY_FIELDS):
            for offer in self:
                old_total = sum(offer[f] for f in offer._INDEMNITY_FIELDS)
                new_total = sum(vals.get(f, offer[f]) for f in offer._INDEMNITY_FIELDS)
                delta = new_total - old_total
                if delta:
                    fyc_updates[offer.id] = offer.final_yearly_costs + delta * 12
        res = super().write(vals)
        for offer in self:
            if offer.id in fyc_updates:
                offer.write({'final_yearly_costs': fyc_updates[offer.id]})
        return res

    @requires_hr_version_context()
    def _get_version(self):
        version = super()._get_version()
        if version:
            diff = {f: self[f] for f in self._INDEMNITY_FIELDS if version[f] != self[f]}
            if diff:
                version.write(diff)
        return version

    @api.depends('l10n_ma_meal_allowance', 'l10n_ma_transport_exemption',
                 'l10n_ma_kilometric_exemption', 'l10n_ma_phone_allowance',
                 'contract_template_id.wage')
    def _compute_salary(self):
        from odoo.addons.hr_contract_salary.utils.hr_version import hr_version_context
        simulation_vals = {}
        with hr_version_context(self, invalidate=True) as offers:
            for offer in offers:
                version = offer._get_version()
                payslip = version._generate_salary_simulation_payslip()
                lv = payslip._get_line_values(['E_CNSS', 'E_AMO', 'NET_INCOME_TAX'])
                pid = payslip.id
                simulation_vals[offer.id] = {
                    'cnss_sal_wage': lv['E_CNSS'][pid]['total'],
                    'amo_sal_wage': lv['E_AMO'][pid]['total'],
                    'ir_wage': lv['NET_INCOME_TAX'][pid]['total'],
                }
        super()._compute_salary()
        for offer in self:
            offer.update(simulation_vals.get(offer.id, {}))
