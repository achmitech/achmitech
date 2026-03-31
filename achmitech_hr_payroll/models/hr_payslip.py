# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, api

import logging

_logger = logging.getLogger(__name__)
from odoo.tools.float_utils import float_round

_GAIN_CAT  = {'BASIC', 'ALW'}
_DED_CAT   = {'DED', 'SALC', 'DEDIRPP', 'UNTAXABLE_DED'}
_INFO_CAT  = {'GROSS', 'INCOME_TAX', 'O_TOTALS', 'UNTAXABLE_DED'}


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_worked_day_lines_values(self, domain=None):
        """Override to count distinct calendar dates per work entry type.

        Odoo's default uses hours / hours_per_day (stored rounded to 2dp).
        For a 44h/week calendar with mixed-hour days (8h weekdays, 4h Saturday),
        this gives 26.19 instead of 26 because 4h / 7.33h_per_day = 0.55 days.

        Morocco payroll counts each calendar work day as 1 day regardless of
        whether it is a full weekday (8h) or a half Saturday (4h).
        number_of_hours is kept unchanged so salary proration stays correct.
        """
        self.ensure_one()
        res = super()._get_worked_day_lines_values(domain=domain)

        calendar = (
            self.version_id.resource_calendar_id
            or self.employee_id.resource_calendar_id
            or self.company_id.resource_calendar_id
        )
        if not calendar or calendar.flexible_hours or calendar.two_weeks_calendar:
            return res

        # Only apply when calendar days have mixed hours (e.g. 8h weekday, 4h Saturday).
        global_att = calendar._get_global_attendances()
        day_hours = {}
        for att in global_att:
            day_hours[att.dayofweek] = day_hours.get(att.dayofweek, 0.0) + (att.hour_to - att.hour_from)
        if len(set(round(h, 2) for h in day_hours.values())) <= 1:
            return res  # All days are equal hours — no correction needed.

        # Count distinct work entry dates per type.
        # Each date = 1 work day regardless of duration.
        we_domain = self.version_id._get_work_hours_domain(
            self.date_from, self.date_to, domain=domain
        )
        groups = self.env['hr.work.entry'].sudo()._read_group(
            we_domain,
            groupby=['work_entry_type_id', 'date:day'],
            aggregates=['id:count'],
        )
        days_by_type = {}
        for wet, _date, _cnt in groups:
            days_by_type[wet.id] = days_by_type.get(wet.id, 0) + 1

        for entry in res:
            type_id = entry['work_entry_type_id']
            if type_id in days_by_type:
                entry['number_of_days'] = float(days_by_type[type_id])

        return res

    def _l10n_ma_net_words(self):
        self.ensure_one()
        try:
            return num2words(round(self.net_wage), lang='fr').capitalize() + ' Dirhams'
        except Exception:
            return ''

    def _l10n_ma_work_days_count(self):
        self.ensure_one()
        lines = self.worked_days_line_ids.filtered(
            lambda w: w.work_entry_type_id.code == 'WORK100'
        )
        return sum(lines.mapped('number_of_days'))

    def _l10n_ma_sum_gain(self):
        self.ensure_one()
        return sum(
            l.total for l in self.line_ids
            if l.appears_on_payslip
            and l.salary_rule_id.category_id.code in _GAIN_CAT
        )

    def _l10n_ma_sum_retenue(self):
        self.ensure_one()
        return sum(
            l.total for l in self.line_ids
            if l.appears_on_payslip
            and l.salary_rule_id.category_id.code in _DED_CAT
        )

    def _l10n_ma_cout_total(self):
        self.ensure_one()
        gross = next(
            (l.total for l in self.line_ids if l.salary_rule_id.code == 'GROSS'), 0.0
        )
        employer = sum(
            l.total for l in self.line_ids
            if l.salary_rule_id.category_id.code == 'SALC' and l.total != 0
        )
        return gross + employer if (gross or employer) else 0.0

    def _l10n_ma_annual_leave(self):
        """Return dict {reliqu, droit, pris, solde} for the main annual leave type.

        Searches allocation-required types including global ones (company_id=False),
        then picks the one with the most allocated days for the employee.
        """
        self.ensure_one()
        try:
            leave_types = self.env['hr.leave.type'].sudo().search([
                '|',
                ('company_id', '=', self.company_id.id),
                ('company_id', '=', False),
                ('requires_allocation', '=', 'yes'),
            ]).with_context(employee_id=self.employee_id.id)
            if not leave_types:
                return None
            # Pick the type with the most allocated days for this employee
            main = max(leave_types, key=lambda t: t.max_leaves or 0)
            if not main.max_leaves and not main.leaves_taken:
                return None
            return {
                'droit':  main.max_leaves or 0.0,
                'pris':   main.leaves_taken or 0.0,
                'solde':  main.virtual_remaining_leaves or 0.0,
                'reliqu': 0.0,
            }
        except Exception:
            return None

    def _l10n_ma_matricule(self):
        self.ensure_one()
        barcode = getattr(self.employee_id, 'barcode', None)
        return barcode or str(self.employee_id.id).zfill(6)

    def _l10n_ma_hire_date(self):
        """Return the current contract version's start date as dd/MM/yyyy, or ''."""
        self.ensure_one()
        try:
            d = self.version_id.contract_date_start
            return d.strftime('%d/%m/%Y') if d else ''
        except Exception:
            return ''

    def _l10n_ma_ir_display(self):
        """Return {'taxable': float, 'rate': float} for the IR row on the bulletin.

        taxable = net taxable salary (GROSS_INCOME_TAX.total after recompute)
        rate    = marginal IR bracket rate (e.g. 30.0)
        Returns None if no IR line found.
        """
        self.ensure_one()
        try:
            # GROSS_INCOME_TAX in MARMONTHLY, IR in 2HAJOB — same concept, different codes
            gross_ic = next(
                (l for l in self.line_ids if l.salary_rule_id.code in ('GROSS_INCOME_TAX', 'IR')), None
            )
            net_ir = next(
                (l for l in self.line_ids if l.salary_rule_id.code == 'NET_INCOME_TAX'), None
            )
            if not gross_ic or not net_ir:
                return None
            net_taxable = gross_ic.total
            # Marginal bracket rate: first bracket where net_taxable <= max_gross
            tax_breakdown = self._rule_parameter('l10n_ma_income_tax_breakdown')
            rate = 0.0
            for max_gross, coef, _ded in tax_breakdown:
                if net_taxable <= max_gross:
                    rate = float(coef)
                    break
            return {
                'taxable': net_taxable,
                'rate': rate,
            }
        except Exception:
            return None
