# -*- coding: utf-8 -*-
{
    'name': 'Portal Leave Approval (Interims)',
    'summary': 'Allow clients to approve/refuse leave requests of their assigned interim employees via the portal.',
    'author': 'ACHMITECH',
    'website': 'https://www.achmitech.com',
    'category': 'Human Resources/Time Off',
    'version': '19.0.1',
    'depends': ['hr_holidays', 'portal', 'project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/mail_templates.xml',
        'data/cron.xml',
        'views/hr_employee_views.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
        'views/portal_leaves_templates.xml',
    ],
    'license': 'LGPL-3',
}
