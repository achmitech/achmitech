# -*- coding: utf-8 -*-
import calendar
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class HrStcWizard(models.TransientModel):
    _name = 'hr.stc.wizard'
    _description = 'Simulateur Solde de Tout Compte'

    # ── Inputs ────────────────────────────────────────────────────────────────
    employee_id = fields.Many2one('hr.employee', string='Employé')
    departure_type = fields.Selection([
        ('demission', 'Démission'),
        ('licenciement', 'Licenciement'),
        ('rupture_conventionnelle', 'Rupture Conventionnelle'),
        ('fin_cdd', 'Fin de CDD'),
    ], string='Type de départ', required=True, default='demission')
    departure_date = fields.Date(string='Date de départ', required=True, default=fields.Date.today)
    contract_start_date = fields.Date(string='Date début contrat')
    wage_type = fields.Selection([
        ('fixed', 'Salaire fixe mensuel'),
        ('hourly', 'Salaire horaire'),
    ], string='Type de salaire', required=True, default='fixed')
    monthly_wage = fields.Float(string='Salaire de base (MAD)')
    hourly_rate = fields.Float(string='Taux horaire (MAD/h)')
    # Non-imposable indemnities (exempt from CNSS/AMO/IR)
    indemnite_transport = fields.Float(string='Indemnité de transport (MAD)')
    indemnite_telephone = fields.Float(string='Indemnité de téléphone (MAD)')
    indemnite_repas = fields.Float(string='Indemnité de repas (MAD)')
    indemnite_kilometrique = fields.Float(string='Indemnité kilométrique (MAD)')
    # Other taxable indemnities (subject to CNSS/AMO/IR)
    indemnites_imposables = fields.Float(string='Autres indemnités imposables (MAD)')
    net_salary = fields.Float(string='Salaire net mensuel (MAD)')
    weekly_hours = fields.Float(string='Heures/semaine', default=44.0)
    days_worked_last_month = fields.Float(string='Jours travaillés ce mois', default=lambda self: self._compute_days_worked(fields.Date.today()))
    unused_leave_days = fields.Float(string='Congés payés non pris (jours)')
    notice_days = fields.Float(string='Préavis non effectué (jours)')

    # ── Computed results ──────────────────────────────────────────────────────
    seniority_years = fields.Float(string='Ancienneté (années)', compute='_compute_stc')
    last_month_salary = fields.Float(string='Salaire dernier mois', compute='_compute_stc')
    indemnite_preavis = fields.Float(string='Indemnité de préavis', compute='_compute_stc')
    indemnite_licenciement = fields.Float(string='Indemnité de licenciement', compute='_compute_stc')
    conges_payes_amount = fields.Float(string='Congés payés non pris', compute='_compute_stc')
    # Deductions on taxable STC gains (CNSS/AMO/IR — licenciement is exempt)
    retenue_cnss = fields.Float(string='Retenue C.N.S.S', compute='_compute_stc')
    retenue_amo = fields.Float(string='Retenue A.M.O.', compute='_compute_stc')
    retenue_ir = fields.Float(string='Retenue IR', compute='_compute_stc')
    total_stc = fields.Float(string='Total gains (brut)', compute='_compute_stc')
    total_retenues = fields.Float(string='Total retenues', compute='_compute_stc')
    net_a_payer = fields.Float(string='Net à payer', compute='_compute_stc')

    # ── Salary conversion helpers ─────────────────────────────────────────────

    def _net_from_gross(self, taxable_base, non_imposable=0.0):
        """Compute net from taxable base + exempt indemnities."""
        if not taxable_base and not non_imposable:
            return 0.0
        date = self.departure_date or fields.Date.today()
        param = self.env['hr.rule.parameter']
        cnss_rate = param._get_parameter_from_code('l10n_ma_cnss', date) / 100.0
        cnss_ceil = param._get_parameter_from_code('l10n_ma_cnss_max', date)
        amo_rate = param._get_parameter_from_code('l10n_ma_amo', date) / 100.0
        ir_brackets = param._get_parameter_from_code('l10n_ma_income_tax_breakdown', date)

        cnss = min(taxable_base, cnss_ceil) * cnss_rate
        amo = taxable_base * amo_rate
        if taxable_base <= 6500:
            frais_pro = min(taxable_base * 0.35, 2500.0)
        else:
            frais_pro = min(taxable_base * 0.25, 35000.0 / 12)
        net_imposable = max(0.0, taxable_base - cnss - amo - frais_pro)

        ir = 0.0
        for ceiling, rate, deduction in ir_brackets:
            if net_imposable <= ceiling:
                ir = max(net_imposable * rate / 100.0 - deduction, 0.0)
                break

        return taxable_base - cnss - amo - ir + non_imposable

    def _deductions_from_taxable(self, taxable_gains):
        """Compute CNSS, AMO, IR on taxable STC gains. Returns (cnss, amo, ir)."""
        if not taxable_gains:
            return 0.0, 0.0, 0.0
        date = self.departure_date or fields.Date.today()
        param = self.env['hr.rule.parameter']
        cnss_rate = param._get_parameter_from_code('l10n_ma_cnss', date) / 100.0
        cnss_ceil = param._get_parameter_from_code('l10n_ma_cnss_max', date)
        amo_rate = param._get_parameter_from_code('l10n_ma_amo', date) / 100.0
        ir_brackets = param._get_parameter_from_code('l10n_ma_income_tax_breakdown', date)

        cnss = min(taxable_gains, cnss_ceil) * cnss_rate
        amo = taxable_gains * amo_rate
        if taxable_gains <= 6500:
            frais_pro = min(taxable_gains * 0.35, 2500.0)
        else:
            frais_pro = min(taxable_gains * 0.25, 35000.0 / 12)
        net_imposable = max(0.0, taxable_gains - cnss - amo - frais_pro)

        ir = 0.0
        for ceiling, rate, deduction in ir_brackets:
            if net_imposable <= ceiling:
                ir = max(net_imposable * rate / 100.0 - deduction, 0.0)
                break

        return cnss, amo, ir

    def _gross_from_net(self, net):
        """Reverse-compute taxable base from net (excluding non-imposable indemnities)."""
        if not net:
            return 0.0
        non_imp = self._total_non_imposable()
        net_taxable = net - non_imp
        lo, hi = max(net_taxable, 0.0), max(net_taxable, 0.0) * 2.5 + 1
        for _ in range(60):
            mid = (lo + hi) / 2.0
            computed = self._net_from_gross(mid, 0.0)
            if abs(computed - net_taxable) < 0.01:
                return round(mid + non_imp, 2)
            if computed < net_taxable:
                lo = mid
            else:
                hi = mid
        return round(mid + non_imp, 2)

    def _total_non_imposable(self):
        return (self.indemnite_transport or 0.0) + (self.indemnite_telephone or 0.0) \
             + (self.indemnite_repas or 0.0) + (self.indemnite_kilometrique or 0.0)

    def _recompute_net(self):
        taxable_base = self.monthly_wage + (self.indemnites_imposables or 0.0)
        self.net_salary = self._net_from_gross(taxable_base, self._total_non_imposable())

    def _monthly_from_hourly(self):
        if self.hourly_rate and self.weekly_hours:
            self.monthly_wage = round(self.hourly_rate * self.weekly_hours * 52 / 12, 2)

    def _hourly_from_monthly(self):
        hours_per_month = self.weekly_hours * 52 / 12 if self.weekly_hours else 0.0
        self.hourly_rate = round(self.monthly_wage / hours_per_month, 4) if hours_per_month else 0.0

    def _compute_days_worked(self, dep_date):
        """Prorated working days for the last month based on departure date.
        Uses calendar-day ratio x 26 (Moroccan standard divisor).
        Full month (last calendar day) -> 26 days.
        """
        if not dep_date:
            return 26.0
        days_in_month = calendar.monthrange(dep_date.year, dep_date.month)[1]
        if dep_date.day >= days_in_month:
            return 26.0
        return round(dep_date.day / days_in_month * 26, 2)

    @api.onchange('departure_date')
    def _onchange_departure_date(self):
        self.days_worked_last_month = self._compute_days_worked(self.departure_date)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            version = self.employee_id.version_id
            if version:
                if version.wage_type == 'hourly':
                    self.wage_type = 'hourly'
                    self.hourly_rate = version.wage
                    self.monthly_wage = 0.0
                else:
                    self.wage_type = 'fixed'
                    self.monthly_wage = version.wage
                self.indemnite_transport = version.l10n_ma_transport_exemption or 0.0
                self.indemnite_telephone = version.l10n_ma_phone_allowance or 0.0
                self.indemnite_repas = version.l10n_ma_meal_allowance or 0.0
                self.indemnite_kilometrique = version.l10n_ma_kilometric_exemption or 0.0
            if self.employee_id.date_start:
                self.contract_start_date = self.employee_id.date_start
        if self.wage_type == 'fixed':
            self._hourly_from_monthly()
        self._recompute_net()

    @api.onchange('wage_type')
    def _onchange_wage_type(self):
        if self.wage_type == 'fixed':
            self._hourly_from_monthly()
        else:
            self._monthly_from_hourly()
        self._recompute_net()

    @api.onchange('monthly_wage', 'indemnites_imposables',
                  'indemnite_transport', 'indemnite_telephone',
                  'indemnite_repas', 'indemnite_kilometrique')
    def _onchange_monthly_wage(self):
        if self.wage_type == 'fixed':
            self._hourly_from_monthly()
        self._recompute_net()

    @api.onchange('hourly_rate', 'weekly_hours')
    def _onchange_hourly(self):
        if self.wage_type == 'hourly':
            self._monthly_from_hourly()
            self._recompute_net()

    @api.depends(
        'departure_type', 'departure_date', 'contract_start_date',
        'wage_type', 'monthly_wage', 'hourly_rate',
        'indemnites_imposables',
        'indemnite_transport', 'indemnite_telephone',
        'indemnite_repas', 'indemnite_kilometrique',
        'weekly_hours',
        'days_worked_last_month', 'unused_leave_days', 'notice_days',
    )
    def _compute_stc(self):
        for rec in self:
            # Seniority
            seniority = 0.0
            if rec.contract_start_date and rec.departure_date:
                rd = relativedelta(rec.departure_date, rec.contract_start_date)
                seniority = rd.years + rd.months / 12 + rd.days / 365.25
            rec.seniority_years = seniority

            total_gross = rec.monthly_wage + (rec.indemnites_imposables or 0.0) + (rec._total_non_imposable())

            # Last month salary (prorated on total gross)
            rec.last_month_salary = total_gross * rec.days_worked_last_month / 26 if total_gross else 0.0

            # Indemnité de préavis (on total gross)
            rec.indemnite_preavis = total_gross * rec.notice_days / 26 if total_gross else 0.0

            # Indemnité de licenciement (Art. 52 — minimum 6 months, exempt from deductions)
            indemnite = 0.0
            if rec.departure_type in ('licenciement', 'rupture_conventionnelle') and seniority >= 0.5 and rec.hourly_rate:
                ind_hours = 0.0
                y1 = min(seniority, 5)
                ind_hours += y1 * 96
                if seniority > 5:
                    y2 = min(seniority - 5, 5)
                    ind_hours += y2 * 144
                if seniority > 10:
                    y3 = min(seniority - 10, 5)
                    ind_hours += y3 * 192
                if seniority > 15:
                    y4 = seniority - 15
                    ind_hours += y4 * 240
                indemnite = ind_hours * rec.hourly_rate
            rec.indemnite_licenciement = indemnite

            # Congés payés non pris (on total gross)
            rec.conges_payes_amount = rec.unused_leave_days * total_gross / 26 if total_gross else 0.0

            # Total gains
            rec.total_stc = rec.last_month_salary + rec.indemnite_preavis + indemnite + rec.conges_payes_amount

            # Deductions applied on taxable portion only (licenciement + non-imposable indemnities are exempt)
            # STC gains were prorated on total_gross — extract only the taxable share
            taxable_base = rec.monthly_wage + (rec.indemnites_imposables or 0.0)
            non_imp = rec._total_non_imposable()
            taxable_stc_gains = (rec.last_month_salary + rec.indemnite_preavis + rec.conges_payes_amount)
            if total_gross:
                taxable_stc_gains = taxable_stc_gains * taxable_base / total_gross
            cnss, amo, ir = rec._deductions_from_taxable(taxable_stc_gains)
            rec.retenue_cnss = cnss
            rec.retenue_amo = amo
            rec.retenue_ir = ir
            rec.total_retenues = cnss + amo + ir
            rec.net_a_payer = rec.total_stc - rec.total_retenues

    def action_print_stc(self):
        return self.env.ref('achmitech_hr_payroll.action_report_stc').report_action(self)
