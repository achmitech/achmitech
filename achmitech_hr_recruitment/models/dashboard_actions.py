# -*- coding: utf-8 -*-
"""
Actions et vues supplémentaires pour le tableau de bord de recrutement
"""

from odoo import models, fields, api


class HrApplicantDashboardActions(models.Model):
    """Ajoute des actions contextuelles au modèle hr.applicant"""
    _inherit = 'hr.applicant'

    @api.model
    def action_view_all_applications(self):
        """Action pour voir toutes les candidatures"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Toutes les Candidatures',
            'res_model': 'hr.applicant',
            'view_mode': 'kanban,tree,form',
            'target': 'current',
        }

    @api.model
    def action_view_applications_by_stage(self):
        """Action pour voir les candidatures par étape"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Candidatures par Étape',
            'res_model': 'hr.applicant',
            'view_mode': 'graph,kanban,tree',
            'target': 'current',
            'context': {'graph_measure': 'id', 'graph_type': 'bar'},
        }

    @api.model
    def action_view_open_positions(self):
        """Action pour voir les postes ouverts"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Postes Ouverts',
            'res_model': 'hr.job',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('state', '=', 'open')],
        }


class HrJobDashboardActions(models.Model):
    """Ajoute des actions contextuelles au modèle hr.job"""
    _inherit = 'hr.job'

    # Nombre de candidatures pour chaque poste
    applicants_count = fields.Integer(
        string="Nombre de Candidatures",
        compute='_compute_applicants_count',
    )

    @api.depends('applicant_ids')
    def _compute_applicants_count(self):
        for job in self:
            job.applicants_count = len(job.applicant_ids)


class HrCandidateDashboardActions(models.Model):
    """Ajoute des champs et actions pour le tableau de bord candidat"""
    _inherit = 'hr.candidate'

    # Nombre d'applications pour chaque candidat
    total_applications = fields.Integer(
        string="Total Candidatures",
        compute='_compute_total_applications',
    )

    # Dernière évaluation reçue
    last_evaluation_id = fields.Many2one(
        comodel_name='hr.applicant.evaluation',
        string="Dernière Évaluation",
        compute='_compute_last_evaluation',
    )

    # Score moyen
    average_score = fields.Float(
        string="Score Moyen",
        compute='_compute_average_score',
    )

    @api.depends('evaluation_ids')
    def _compute_total_applications(self):
        for candidate in self:
            candidate.total_applications = self.env['hr.applicant'].search_count([
                ('candidate_id', '=', candidate.id)
            ])

    @api.depends('evaluation_ids')
    def _compute_last_evaluation(self):
        for candidate in self:
            evaluations = candidate.evaluation_ids.sorted('date', reverse=True)
            candidate.last_evaluation_id = evaluations[0] if evaluations else False

    @api.depends('evaluation_ids')
    def _compute_average_score(self):
        for candidate in self:
            if candidate.evaluation_ids:
                scores = [int(ev.rating) for ev in candidate.evaluation_ids if ev.rating]
                if scores:
                    candidate.average_score = sum(scores) / len(scores)
                else:
                    candidate.average_score = 0
            else:
                candidate.average_score = 0
