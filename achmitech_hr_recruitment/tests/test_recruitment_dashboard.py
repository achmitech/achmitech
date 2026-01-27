# -*- coding: utf-8 -*-
"""
Tests pour le Tableau de Bord de Recrutement
Vérifier que toutes les fonctionnalités fonctionnent correctement
"""

from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta


class TestRecruitmentDashboard(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.dashboard_model = self.env['recruitment.dashboard']
        self.applicant_model = self.env['hr.applicant']
        self.evaluation_model = self.env['hr.applicant.evaluation']
        self.job_model = self.env['hr.job']

    def test_get_dashboard_data_structure(self):
        """Vérifier que get_dashboard_data retourne la bonne structure"""
        data = self.dashboard_model.get_dashboard_data()
        
        # Vérifier les clés principales
        required_keys = [
            'total_applicants',
            'total_candidates',
            'open_jobs',
            'new_applicants_week',
            'conversion_rate',
            'applicants_by_stage',
            'evaluations_by_rating',
            'top_jobs',
            'interviews_this_week',
            'unevaluated_count',
        ]
        
        for key in required_keys:
            self.assertIn(key, data, f"La clé '{key}' est manquante dans les données du dashboard")

    def test_applicants_by_stage(self):
        """Vérifier que _get_applicants_by_stage retourne les candidatures groupées par étape"""
        data = self.dashboard_model._get_applicants_by_stage()
        
        # Vérifier que c'est une liste
        self.assertIsInstance(data, list)
        
        # Vérifier la structure des éléments
        for item in data:
            self.assertIn('stage_name', item)
            self.assertIn('count', item)
            self.assertIn('stage_id', item)

    def test_evaluations_by_rating(self):
        """Vérifier que _get_evaluations_by_rating retourne les évaluations groupées par score"""
        data = self.dashboard_model._get_evaluations_by_rating()
        
        # Vérifier que c'est une liste
        self.assertIsInstance(data, list)
        
        # Vérifier qu'il y a 5 ratings (très défavorable à très favorable)
        self.assertEqual(len(data), 5)
        
        # Vérifier la structure
        for item in data:
            self.assertIn('rating', item)
            self.assertIn('count', item)
            self.assertIn('rating_value', item)

    def test_top_jobs(self):
        """Vérifier que _get_top_jobs retourne les top postes"""
        data = self.dashboard_model._get_top_jobs(limit=5)
        
        # Vérifier que c'est une liste
        self.assertIsInstance(data, list)
        
        # Vérifier la limite
        self.assertLessEqual(len(data), 5)
        
        # Si des données existent, vérifier la structure
        if data:
            for item in data:
                self.assertIn('job_name', item)
                self.assertIn('count', item)
                self.assertIn('job_id', item)

    def test_interviews_this_week(self):
        """Vérifier que _get_interviews_this_week retourne les entretiens de la semaine"""
        data = self.dashboard_model._get_interviews_this_week()
        
        # Vérifier que c'est une liste
        self.assertIsInstance(data, list)
        
        # Vérifier la structure si des données existent
        if data:
            for item in data:
                self.assertIn('candidate_name', item)
                self.assertIn('job_name', item)
                self.assertIn('stage_name', item)
                self.assertIn('date', item)
                self.assertIn('interviewer', item)

    def test_unevaluated_applicants(self):
        """Vérifier que _get_unevaluated_applicants retourne les candidatures non évaluées"""
        data = self.dashboard_model._get_unevaluated_applicants()
        
        # Vérifier que c'est un recordset
        self.assertIsNotNone(data)

    def test_dashboard_computations(self):
        """Vérifier que les computations du dashboard ne plantent pas"""
        try:
            data = self.dashboard_model.get_dashboard_data()
            
            # Vérifier que les nombres sont des entiers
            self.assertIsInstance(data['total_applicants'], int)
            self.assertIsInstance(data['total_candidates'], int)
            self.assertIsInstance(data['open_jobs'], int)
            self.assertIsInstance(data['new_applicants_week'], int)
            
            # Vérifier que le taux de conversion est entre 0 et 100
            self.assertGreaterEqual(data['conversion_rate'], 0)
            self.assertLessEqual(data['conversion_rate'], 100)
            
        except Exception as e:
            self.fail(f"get_dashboard_data a levé une exception: {e}")


class TestDashboardActions(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.hr_applicant = self.env['hr.applicant']
        self.hr_job = self.env['hr.job']
        self.hr_candidate = self.env['hr.candidate']

    def test_hr_applicant_actions(self):
        """Vérifier que les actions du modèle hr.applicant existent"""
        # Vérifier que les méthodes existent
        self.assertTrue(hasattr(self.hr_applicant, 'action_view_all_applications'))
        self.assertTrue(hasattr(self.hr_applicant, 'action_view_applications_by_stage'))
        self.assertTrue(hasattr(self.hr_applicant, 'action_view_open_positions'))

    def test_hr_job_applicants_count(self):
        """Vérifier que le champ applicants_count fonctionne"""
        # Vérifier que le champ existe
        self.assertIn('applicants_count', self.hr_job._fields)

    def test_hr_candidate_computed_fields(self):
        """Vérifier que les champs calculés du candidat existent"""
        required_fields = [
            'total_applications',
            'last_evaluation_id',
            'average_score',
        ]
        
        for field in required_fields:
            self.assertIn(field, self.hr_candidate._fields)
