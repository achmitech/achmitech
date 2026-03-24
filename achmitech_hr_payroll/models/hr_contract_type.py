# -*- coding: utf-8 -*-
from odoo import fields, models


class HrContractTypeSignDocument(models.Model):
    _name = 'achmitech.contract.type.sign.document'
    _description = 'Document de signature par type de contrat'
    _order = 'sequence, id'

    contract_type_id = fields.Many2one(
        'hr.contract.type', string='Type de contrat', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    report_id = fields.Many2one(
        'ir.actions.report', string='Rapport QWeb', required=True,
        domain=[('report_type', '=', 'qweb-pdf')])
    employee_label = fields.Char(
        string='Texte zone signature Salarié', required=True,
        help="Texte recherché dans le PDF pour localiser la zone de signature du salarié")
    employer_label = fields.Char(
        string='Texte zone signature Employeur', required=True,
        help="Texte recherché dans le PDF pour localiser la zone de signature de l'employeur")


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    sign_document_ids = fields.One2many(
        'achmitech.contract.type.sign.document', 'contract_type_id',
        string='Documents de signature')
