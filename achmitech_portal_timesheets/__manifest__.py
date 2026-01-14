# -*- coding: utf-8 -*-
{
    'name': "achmitech_portal_timesheets",

    'summary': "Portal Timesheet Management & Validation",

    'description': """
        Portal Timesheet Management & Validation

        This module extends the Odoo Portal to allow external collaborators, consultants, and interim workers to 
        securely report their working time directly on assigned projects and tasks.

        It provides an intuitive portal interface to view task details, submit timesheet entries, and track
        reported hours, while ensuring that only authorized and assigned users can log time on specific tasks.
    """,

    'author': "Ayoub Jbili - ACHMITECH",
    'website': "https://www.achmitech.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Services/Timesheets',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'hr_timesheet'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/project_task.xml',
        'views/portal_task_template.xml',
    ],
    
    'license': 'LGPL-3',
}

