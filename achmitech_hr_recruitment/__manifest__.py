# -*- coding: utf-8 -*-
{
    'name': "achmitech_hr_recruitment",

    'summary': "Gestion avancée des candidatures et des évaluations",

    'description': """
Ce module étend les fonctionnalités de recrutement d'Odoo pour permettre une gestion
avancée des candidats, de leurs candidatures et de leurs évaluations.

Il centralise l'historique des entretiens, décisions et scores au niveau du candidat,
permettant une vision globale du parcours de recrutement à travers plusieurs offres
d'emploi et processus d'évaluation.

Le module est conçu pour s'adapter à des workflows de recrutement complexes, incluant
plusieurs intervenants (recruteurs, intervieweurs, managers) et des règles d'accès
différenciées, tout en restant compatible avec un environnement multi-sociétés.

Il constitue une base évolutive pour la gestion du talent, la prise de décision et le
pilotage des processus de recrutement.
    """,

    'author': "Ayoub Jbili - ACHMITECH",
    'website': "https://www.achmitech.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources/Recruitment',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr_recruitment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_recruitment_dashboard.xml',
        'views/hr_recruitment_dashboard_advanced.xml',
        'views/hr_recrutement_applicant_form.xml',
        'views/hr_recruitement_stage.xml',
        'reports/hr_candidate_report.xml'
    ],
    
    'license': 'LGPL-3',
}

