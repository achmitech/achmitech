# achmitech_hr_payroll

**Odoo 19 — Moroccan HR & Payroll Extensions for ACHMITECH**

Extends `l10n_ma_hr_payroll`, `hr_contract_salary`, and `hr_contract_salary_payroll` with:

- Dynamic contract PDF generation (CDI, Lettre d'Engagement de Stage) merged into a single signable document
- Ordre de Mission generation per contract type
- HR letter wizard (Certificat de Travail, Attestation de Stage, Renouvellement/Rupture PE, Aménagement Stage)
- Offer document preview before sending to the candidate/employee
- Custom departure reasons
- Moroccan payroll fields: phone/internet allowance (`l10n_ma_phone_allowance`), annual gross wage display
- Sign template auto-injection for active-employee contract updates

## Dependencies

| Module | Role |
|---|---|
| `l10n_ma_hr_payroll` | Moroccan salary structure (MARMONTHLY), transport/meal/kilometric allowances |
| `hr_contract_salary` | Salary offer, salary configurator, `hr.version` contract versions |
| `hr_contract_salary_payroll` | `monthly_wage`, payroll simulation on offer |

## Module Structure

```
achmitech_hr_payroll/
├── controllers/
│   └── controllers.py          # Submit override: sign template injection + dynamic PDF merge
├── data/
│   ├── hr_salary_rule_data.xml         # PHONE_A salary rule
│   ├── hr_personal_info_data.xml       # Personal info fields on offer form
│   ├── hr_contract_salary_benefit_data.xml  # Benefit sliders (meal, transport, phone, km)
│   ├── hr_contract_salary_resume_data.xml   # Salary resume lines
│   └── hr_departure_reason_data.xml    # Custom departure reasons
├── models/
│   ├── hr_version.py                   # sign_wage_annual_gross, client_id, mission_order_ref, phone allowance
│   ├── hr_employee.py                  # sign_* computed fields for sign template pre-fill
│   ├── hr_contract_type.py             # sign_document_ids: reports + signature zones per contract type
│   ├── hr_contract_salary_offer.py     # action_preview_offer_documents
│   ├── hr_contract_salary_resume.py    # Additional payroll codes (CNSS, AMO, IR, CIMR)
│   ├── hr_job.py                       # internship_missions, internship_supervisor_id
│   └── hr_letter_wizard.py             # TransientModel for HR letter generation
├── security/
│   └── ir.model.access.csv
└── views/
    ├── contract_report.xml             # CDI contract + Ordre de Mission QWeb reports
    ├── lettre_engagement_report.xml    # Lettre d'Engagement de Stage QWeb report
    ├── hr_letter_reports.xml           # Attestation de Stage, Certificat de Travail, Renouvellement PE, Rupture PE, Aménagement Stage
    ├── hr_letter_wizard_views.xml      # Wizard views + Action menu bindings
    ├── hr_offer_views.xml              # Offer form: allowances, client, mission ref, preview button
    ├── hr_contract_type_views.xml      # Sign documents configuration per contract type
    ├── hr_employee_views.xml
    └── hr_job_views.xml
```

## Upgrade Command

```bash
/usr/bin/odoo -c /etc/odoo/odoo.conf -d odoo19 -u achmitech_hr_payroll \
  --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo --stop-after-init
```

## Author

Ayoub Jbili — ACHMITECH
