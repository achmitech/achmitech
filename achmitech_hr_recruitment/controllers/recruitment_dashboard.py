# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class RecruitmentDashboardController(http.Controller):
    
    @http.route('/recruitment/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self):
        """API endpoint pour récupérer les données du tableau de bord"""
        dashboard = request.env['recruitment.dashboard'].get_dashboard_data()
        return dashboard

    @http.route('/recruitment/dashboard', type='http', auth='user')
    def dashboard_view(self):
        """Vue du tableau de bord recrutement"""
        values = {
            'dashboard_data': request.env['recruitment.dashboard'].get_dashboard_data(),
        }
        return request.render('achmitech_hr_recruitment.recruitment_dashboard_template', values)
