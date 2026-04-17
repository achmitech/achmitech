# -*- coding: utf-8 -*-
from odoo import models, fields


class HrSalarySimulatorConfig(models.Model):
    _name = 'hr.salary.simulator.config'
    _description = 'Configuration simulateur de salaire'

    structure_type_id = fields.Many2one(
        'hr.payroll.structure.type', string='Type de structure', required=True,
    )
    input_line_ids = fields.One2many(
        'hr.salary.simulator.config.input', 'config_id', string='Indemnités à afficher',
    )
    output_line_ids = fields.One2many(
        'hr.salary.simulator.config.line', 'config_id', string='Lignes de résultat',
    )

    _unique_structure_type = models.Constraint(
        'UNIQUE(structure_type_id)',
        'Une configuration existe déjà pour ce type de structure.',
    )


class HrSalarySimulatorConfigInput(models.Model):
    _name = 'hr.salary.simulator.config.input'
    _description = 'Indemnité simulateur — entrée'
    _order = 'sequence'

    config_id = fields.Many2one('hr.salary.simulator.config', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Libellé', required=True)
    field_id = fields.Many2one(
        'ir.model.fields', string='Champ hr.version', required=True,
        domain=[('model', '=', 'hr.version'), ('ttype', 'in', ['monetary', 'float', 'integer'])],
        ondelete='cascade',
    )
    field_name = fields.Char(related='field_id.name', store=True, readonly=True)


class HrSalarySimulatorConfigLine(models.Model):
    _name = 'hr.salary.simulator.config.line'
    _description = 'Ligne résultat simulateur'
    _order = 'sequence'

    config_id = fields.Many2one('hr.salary.simulator.config', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Libellé', required=True)
    rule_ids = fields.Many2many(
        'hr.salary.rule', string='Règles salariales',
        help="Les totaux de toutes les règles sélectionnées seront additionnés sur cette ligne.",
    )
