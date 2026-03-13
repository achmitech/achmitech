# -*- coding: utf-8 -*-
{
    'name': "achmitech_hr_payroll",
    'summary': "Extensions paie Maroc - ACHMITECH",
    'category': 'Human Resources/Payroll',
    'version': "19.0.1",
    'author': "Ayoub Jbili - ACHMITECH",
    'website': "https://www.achmitech.com",
    'depends': ['l10n_ma_hr_payroll', 'hr_contract_salary', 'hr_contract_salary_payroll'],
    'data': [
        'data/hr_salary_rule_data.xml',
        'data/hr_personal_info_data.xml',
        'data/hr_contract_salary_benefit_data.xml',
        'data/hr_contract_salary_resume_data.xml',
        'data/sign_item_type_data.xml',
        'views/hr_employee_views.xml',
        'views/hr_offer_views.xml',
    ],
    'license': 'LGPL-3',
}
