# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api
from odoo.addons.hr_contract_salary.utils.hr_version import requires_hr_version_context

class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_ma_phone_allowance = fields.Monetary(string="Téléphone / Internet")
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

    # Non-stored computed fields for sign template pre-fill.
    # Non-stored = computed fresh at read time on the sudo recordset used by
    # the hr_contract_salary submit controller, AFTER _update_personal_info
    # has already written the address/birthday to the version/employee.
    # Direct field paths that work as-is (type in the sign item placeholder):
    #   identification_id, country_id.name, employee_id.place_of_birth,
    #   private_street, private_zip, private_city, employee_id.legal_name,
    #   mission_order_ref, client_id.name,
    #   job_title (titre du poste, ex: "Consultant RH"), job_id.name (poste)
    sign_birthday = fields.Char(compute='_compute_sign_fields', string="Date de naissance (signe)")
    sign_address = fields.Char(compute='_compute_sign_fields', string="Adresse (signe)")
    sign_client = fields.Char(compute='_compute_sign_fields', string="Client (signe)")
    sign_start_date = fields.Char(compute='_compute_sign_fields', string="Date de démarrage (signe)")
    sign_wage_yearly = fields.Char(compute='_compute_sign_fields', string="Salaire annuel en chiffres (signe)")
    sign_wage_yearly_words = fields.Char(compute='_compute_sign_fields', string="Salaire annuel en lettres (signe)")
    sign_phone_allowance = fields.Char(compute='_compute_sign_fields', string="Téléphone (signe)")
    sign_meal_allowance = fields.Char(compute='_compute_sign_fields', string="Panier (signe)")
    sign_transport = fields.Char(compute='_compute_sign_fields', string="Transport (signe)")
    sign_indemnites_block = fields.Char(compute='_compute_sign_fields', string="Bloc indemnités (signe)")

    # Total character width used to pad sign fields on both sides with '#'.
    # Tune this to match the width of your sign template text boxes.
    _SIGN_FIELD_WIDTH = 30

    def _get_whitelist_fields_from_template(self):
        fields = super()._get_whitelist_fields_from_template()
        if self.env.company.country_id.code == 'MA':
            fields += ['l10n_ma_phone_allowance']
        return fields

    @api.depends('employee_id.birthday',
                 'private_street', 'private_street2', 'private_city', 'private_zip', 'private_country_id',
                 'client_id', 'contract_date_start', 'wage', 'final_yearly_costs',
                 'l10n_ma_phone_allowance', 'l10n_ma_meal_allowance', 'l10n_ma_transport_exemption')
    def _compute_sign_fields(self):
        for v in self:
            v.sign_birthday = v.employee_id.birthday.strftime('%d/%m/%Y') if v.employee_id.birthday else ''
            v.sign_address = ', '.join(filter(None, [
                v.private_street, v.private_street2, v.private_zip, v.private_city,
                v.private_country_id.name,
            ]))
            v.sign_client = v.client_id.name if v.client_id else ''
            v.sign_start_date = v.contract_date_start.strftime('%d/%m/%Y') if v.contract_date_start else ''
            v.sign_wage_yearly = self._pad(self._fmt_amount(v.final_yearly_costs))
            v.sign_wage_yearly_words = self._pad(self._fmt_amount_words(v.final_yearly_costs))
            v.sign_phone_allowance = self._fmt_amount(v.l10n_ma_phone_allowance)
            v.sign_meal_allowance = self._fmt_amount(v.l10n_ma_meal_allowance)
            v.sign_transport = self._fmt_amount(v.l10n_ma_transport_exemption)
            clauses = []
            if v.l10n_ma_transport_exemption:
                clauses.append(
                    f"Il sera versé une indemnité mensuelle forfaitaire de transport de "
                    f"{int(v.l10n_ma_transport_exemption)} dirhams par mois."
                )
            if v.l10n_ma_phone_allowance:
                clauses.append(
                    f"Le Salarié devant être joignable et pouvoir travailler à distance, "
                    f"il bénéficiera du remboursement de Téléphone / Internet dans la limite de "
                    f"{int(v.l10n_ma_phone_allowance)} dirhams par mois."
                )
            if v.l10n_ma_meal_allowance:
                clauses.append(
                    f"Le Salarié bénéficiera d'une prime de panier mensuelle de "
                    f"{int(v.l10n_ma_meal_allowance)} dirhams par mois en raison du travail continu."
                )
            if clauses:
                intro = "Dans le cadre de sa mission, le collaborateur bénéficiera des frais suivants :\n"
                closing = "\nCes frais sont mentionnés sur le bulletin de salaires et versés chaque mois au collaborateur. Ils seront proratisés les moiss d'entrée et de sortie, ainsi qu'en cas d'absence de longue durée (hors congés)."
                v.sign_indemnites_block = intro + "\n".join(clauses) + closing
            else:
                v.sign_indemnites_block = ""

    @staticmethod
    def _fmt_amount(amount):
        # French format: space as thousands separator, comma as decimal, e.g. "5 000,00 MAD"
        integer, decimal = f"{amount:.2f}".split('.')
        integer_fmt = '{:,}'.format(int(integer)).replace(',', '\u00a0')  # non-breaking space
        return f"{integer_fmt},{decimal} MAD"

    @staticmethod
    def _fmt_amount_words(amount):
        # French words, e.g. "soixante mille dirhams"
        words = num2words(int(amount), lang='fr')
        return f"{words} dirhams"

    @classmethod
    def _pad(cls, value):
        # Center the value within _SIGN_FIELD_WIDTH chars, padding both sides with '#'.
        # If the value is longer than the width, it is returned as-is.
        return value.center(cls._SIGN_FIELD_WIDTH, '#')


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
