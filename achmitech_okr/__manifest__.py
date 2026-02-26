{
    'name': "OKR Tracking",

    'summary': "OKR tracking and staffing plan management for recruitment agencies",

    'description': """
Track Objectives and Key Results (OKRs) for recruiters.
Manage staffing plans, staffing needs, and KPI metrics linked to recruitment activity.
    """,

    'author': "Ayoub Jbili",
    'website': "https://www.achmitech.com",

    'category': 'Human Resources',
    'version': '19.0.1.0.0',

    'depends': ['base', 'mail', 'hr', 'hr_recruitment', 'achmitech_hr_recruitment'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/staffing_data.xml',
        'views/staffing_plan_views.xml',
        'views/hr_applicant_views.xml',
        'wizard/applicant_get_refuse_reason_views.xml',
        'wizard/okr_recontact_wizard_views.xml',
        'views/res_company_configuration.xml',
        'views/okr_node_views.xml',
        'views/okr_node_metric_views.xml',
        'views/okr_metric_definition.xml',
        'views/okr_node_progress_inherit.xml',
        'views/okr_menus.xml',
    ],
    # only loaded in demonstration mode
    'assets': {
        'web.assets_backend_lazy': [
            'achmitech_okr/static/src/views/**/*',
        ],
    },
}

