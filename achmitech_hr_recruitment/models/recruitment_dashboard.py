# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import date_utils
from datetime import datetime, timedelta


class RecruitmentDashboard(models.Model):
    _name = "recruitment.dashboard"
    _description = "Tableau de Bord de Recrutement"

    @api.model
    def get_dashboard_data(self):
        """Récupère les données du tableau de bord de recrutement"""
        
        # Statistiques générales
        total_applicants = self.env['hr.applicant'].search_count([])
        total_candidates = self.env['hr.candidate'].search_count([])
        
        # Candidatures par étape
        applicants_by_stage = self._get_applicants_by_stage()
        
        # Évaluations par score
        evaluations_by_rating = self._get_evaluations_by_rating()
        
        # Candidats cette semaine
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        new_applicants_week = self.env['hr.applicant'].search_count([
            ('create_date', '>=', week_start)
        ])
        
        # Postes ouverts
        open_jobs = self.env['hr.job'].search_count([('state', '=', 'open')])
        
        # Taux de conversion (candidatures ayant atteint la dernière étape)
        last_stage_applicants = self.env['hr.applicant'].search_count([
            ('stage_id.sequence', '=', 
             self.env['hr.recruitment.stage'].search([], order='sequence desc', limit=1).sequence)
        ]) if self.env['hr.recruitment.stage'].search([], order='sequence desc', limit=1) else 0
        
        conversion_rate = round((last_stage_applicants / total_applicants * 100), 2) if total_applicants > 0 else 0
        
        # Top 5 postes avec le plus de candidatures
        top_jobs = self._get_top_jobs()
        
        # Entretiens programmés cette semaine
        interviews_this_week = self._get_interviews_this_week()
        
        # Candidatures sans évaluation
        unevaluated_applicants = self._get_unevaluated_applicants()
        
        return {
            'total_applicants': total_applicants,
            'total_candidates': total_candidates,
            'open_jobs': open_jobs,
            'new_applicants_week': new_applicants_week,
            'conversion_rate': conversion_rate,
            'applicants_by_stage': applicants_by_stage,
            'evaluations_by_rating': evaluations_by_rating,
            'top_jobs': top_jobs,
            'interviews_this_week': interviews_this_week,
            'unevaluated_count': len(unevaluated_applicants),
        }

    def _get_applicants_by_stage(self):
        """Candidatures par étape"""
        stages = self.env['hr.recruitment.stage'].search([])
        data = []
        for stage in stages:
            count = self.env['hr.applicant'].search_count([('stage_id', '=', stage.id)])
            data.append({
                'stage_name': stage.name,
                'count': count,
                'stage_id': stage.id,
            })
        return sorted(data, key=lambda x: x['count'], reverse=True)

    def _get_evaluations_by_rating(self):
        """Distribution des évaluations par score"""
        ratings = [
            ('5', 'Très défavorable'),
            ('4', 'Défavorable'),
            ('3', 'À évaluer'),
            ('2', 'Favorable'),
            ('1', 'Très favorable'),
        ]
        data = []
        for rating_value, rating_label in ratings:
            count = self.env['hr.applicant.evaluation'].search_count([('rating', '=', rating_value)])
            data.append({
                'rating': rating_label,
                'count': count,
                'rating_value': rating_value,
            })
        return data

    def _get_top_jobs(self, limit=5):
        """Top 5 postes avec le plus de candidatures"""
        query = """
            SELECT job_id, COUNT(*) as count
            FROM hr_applicant
            WHERE job_id IS NOT NULL
            GROUP BY job_id
            ORDER BY count DESC
            LIMIT %s
        """
        self.env.cr.execute(query, (limit,))
        results = self.env.cr.fetchall()
        
        data = []
        for job_id, count in results:
            job = self.env['hr.job'].browse(job_id)
            data.append({
                'job_name': job.name,
                'count': count,
                'job_id': job_id,
            })
        return data

    def _get_interviews_this_week(self):
        """Entretiens programmés cette semaine"""
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        week_end = week_start + timedelta(days=7)
        
        evaluations = self.env['hr.applicant.evaluation'].search([
            ('date', '>=', week_start),
            ('date', '<', week_end),
        ], order='date asc', limit=10)
        
        data = []
        for eval in evaluations:
            data.append({
                'candidate_name': eval.candidate_id.name if eval.candidate_id else eval.applicant_id.partner_name,
                'job_name': eval.job_id.name,
                'stage_name': eval.stage_id.name,
                'date': eval.date,
                'interviewer': eval.interviewer_id.name,
            })
        return data

    def _get_unevaluated_applicants(self):
        """Candidatures sans aucune évaluation"""
        unevaluated = self.env['hr.applicant'].search([
            ('evaluation_ids', '=', False)
        ], limit=10)
        return unevaluated
