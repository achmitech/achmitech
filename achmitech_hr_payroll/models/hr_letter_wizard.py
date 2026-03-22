# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrLetterWizard(models.TransientModel):
    _name = 'hr.letter.wizard'
    _description = 'Assistant Lettres RH'

    letter_type = fields.Selection([
        ('certificat_travail', "Certificat de travail"),
        ('attestation_stage', "Attestation de stage"),
        ('renouvellement_pe', "Renouvellement période d'essai"),
        ('rupture_pe', "Rupture période d'essai"),
        ('amenagement_stage', "Aménagement durée du stage"),
    ], required=True)

    employee_id = fields.Many2one('hr.employee', string="Employé(e)", required=True)
    version_id = fields.Many2one('hr.version', string="Contrat")

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and not self.version_id:
            self.version_id = self.employee_id.version_id

    # Renouvellement PE
    pe_initial_end_date = fields.Date("Fin PE initiale")
    pe_new_end_date = fields.Date("Nouvelle fin PE")

    # Rupture PE
    termination_date = fields.Date("Date de rupture")
    notice_days = fields.Integer("Jours de préavis (ouvrés)")
    paid_until_date = fields.Date("Rémunéré(e) jusqu'au")

    # Aménagement Stage
    engagement_letter_date = fields.Date("Date lettre d'engagement")
    new_end_date = fields.Date("Nouvelle date de fin de stage")

    def action_print(self):
        if self.letter_type == 'certificat_travail':
            return self.env.ref(
                'achmitech_hr_payroll.action_report_certificat_travail'
            ).report_action(self)
        if self.letter_type == 'attestation_stage':
            # report is bound to hr.version, pass the version record directly
            return self.env.ref(
                'achmitech_hr_payroll.action_report_attestation_stage'
            ).report_action(self.version_id)
        report_xmlids = {
            'renouvellement_pe': 'achmitech_hr_payroll.action_report_renouvellement_pe',
            'rupture_pe': 'achmitech_hr_payroll.action_report_rupture_pe',
            'amenagement_stage': 'achmitech_hr_payroll.action_report_amenagement_stage',
        }
        return self.env.ref(report_xmlids[self.letter_type]).report_action(self)
