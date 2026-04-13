# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.hr_contract_salary.utils.hr_version import hr_version_context
from odoo import SUPERUSER_ID


class HrSalarySimulatorBenefit(models.TransientModel):
    _name = 'hr.salary.simulator.benefit'
    _description = 'Salary Simulator Benefit Input'
    _order = 'sequence'

    wizard_id = fields.Many2one('hr.salary.simulator', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char()
    field_name = fields.Char()
    value = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id')


class HrSalarySimulatorLine(models.TransientModel):
    _name = 'hr.salary.simulator.line'
    _description = 'Salary Simulator Result Line'
    _order = 'sequence'

    wizard_id = fields.Many2one('hr.salary.simulator', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(readonly=True)
    total = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id')


class HrSalarySimulator(models.TransientModel):
    _name = 'hr.salary.simulator'
    _description = 'Simulateur de salaire'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    structure_id = fields.Many2one('hr.payroll.structure', string='Structure salariale', required=True)
    wage_type = fields.Selection(related='structure_id.type_id.wage_type', string='Type de salaire')
    resource_calendar_id = fields.Many2one(
        'resource.calendar', string='Horaire de travail',
        default=lambda self: self.env.company.resource_calendar_id,
    )

    monthly_wage = fields.Monetary(string='Salaire brut mensuel')
    hourly_wage = fields.Monetary(string='Taux horaire')
    target_net_wage = fields.Monetary(string='Net souhaité (laisser vide si brut connu)')

    benefit_line_ids = fields.One2many('hr.salary.simulator.benefit', 'wizard_id', string='Indemnités')
    result_line_ids = fields.One2many('hr.salary.simulator.line', 'wizard_id', string='Résultat', readonly=True)

    net_wage = fields.Monetary(string='Net', readonly=True)
    gross_wage = fields.Monetary(string='Brut', readonly=True)
    no_config_warning = fields.Boolean(readonly=True)

    # ── Structure change ──────────────────────────────────────────────────────

    def _get_config(self):
        return self.env['hr.salary.simulator.config'].search([
            ('structure_type_id', '=', self.structure_id.type_id.id),
        ], limit=1)

    @api.onchange('structure_id')
    def _onchange_structure_id(self):
        self.benefit_line_ids = [(5,)]
        self.result_line_ids = [(5,)]
        self.no_config_warning = False
        if not self.structure_id:
            return
        if self.wage_type == 'hourly':
            self.target_net_wage = 0.0

        config = self._get_config()
        if config:
            self.benefit_line_ids = [(0, 0, {
                'sequence': l.sequence,
                'name': l.name,
                'field_name': l.field_name,
                'value': 0.0,
            }) for l in config.input_line_ids]
        else:
            self.no_config_warning = True

    # ── Simulation ────────────────────────────────────────────────────────────

    def _build_version_vals(self):
        wage_field = 'hourly_wage' if self.wage_type == 'hourly' else 'wage'
        wage_value = self.hourly_wage if self.wage_type == 'hourly' else self.monthly_wage
        vals = {
            'structure_type_id': self.structure_id.type_id.id,
            'contract_date_start': fields.Date.today(),
            wage_field: wage_value,
            'wage_with_holidays': wage_value,
        }
        if self.resource_calendar_id:
            vals['resource_calendar_id'] = self.resource_calendar_id.id
        for line in self.benefit_line_ids:
            if line.field_name:
                vals[line.field_name] = line.value or 0.0
        return vals

    def _run_simulation(self, version_vals):
        result = {}
        with hr_version_context(self, invalidate=False) as ctx_self:
            employee = ctx_self.env['hr.employee'].with_user(SUPERUSER_ID).sudo().create({
                'name': 'Simulation Employee',
                'active': False,
                'company_id': ctx_self.company_id.id,
                'country_id': ctx_self.company_id.country_id.id,
                'private_country_id': ctx_self.company_id.country_id.id,
                'certificate': False,
            })
            version = employee.current_version_id
            version.write(version_vals)
            version.flush_recordset()
            ps = version._generate_salary_simulation_payslip()

            config = self._get_config()
            if config and config.output_line_ids:
                codes = [r.code for line in config.output_line_ids for r in line.rule_ids if r.code]
                lv = ps._get_line_values(codes)
                lines = []
                for i, cfg_line in enumerate(config.output_line_ids, start=1):
                    total = sum(
                        lv.get(r.code, {}).get(ps.id, {}).get('total', 0.0)
                        for r in cfg_line.rule_ids if r.code
                    )
                    lines.append({
                        'sequence': i,
                        'name': cfg_line.name,
                        'total': total,
                    })
            else:
                lines = [
                    {'sequence': i, 'name': pl.name, 'total': pl.total}
                    for i, pl in enumerate(ps.line_ids.filtered('appears_on_payslip'), start=1)
                ]

            net_line = ps.line_ids.filtered(lambda l: l.code == 'NET')
            gross_line = ps.line_ids.filtered(lambda l: l.code == 'GROSS')
            result['lines'] = lines
            result['net'] = net_line[:1].total if net_line else 0.0
            result['gross'] = gross_line[:1].total if gross_line else 0.0
        return result

    def action_simulate(self):
        self.ensure_one()
        if self.target_net_wage:
            self._solve_gross_from_net()
        else:
            self._compute_result()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _compute_result(self):
        vals = self._build_version_vals()
        sim = self._run_simulation(vals)
        self.net_wage = sim['net']
        self.gross_wage = sim['gross'] or (self.hourly_wage if self.wage_type == 'hourly' else self.monthly_wage)
        self.result_line_ids = [(5,)] + [(0, 0, l) for l in sim['lines']]

    def _solve_gross_from_net(self):
        target = self.target_net_wage
        wage_field = 'hourly_wage' if self.wage_type == 'hourly' else 'wage'
        x0, x1 = 0.0, target * 2.0
        base_vals = self._build_version_vals()

        def _sim(gross):
            vals = dict(base_vals)
            vals[wage_field] = gross
            vals['wage_with_holidays'] = gross
            return self._run_simulation(vals)['net']

        f0 = _sim(x0) - target
        f1 = _sim(x1) - target
        for _ in range(10):
            if abs(f1) < 0.5:
                break
            if abs(f1 - f0) < 1e-9:
                break
            x2 = max(0.0, x1 - f1 * (x1 - x0) / (f1 - f0))
            x0, f0 = x1, f1
            x1, f1 = x2, _sim(x2) - target

        gross = round(x1, 2)
        if self.wage_type == 'hourly':
            self.hourly_wage = gross
        else:
            self.monthly_wage = gross
        self._compute_result()
