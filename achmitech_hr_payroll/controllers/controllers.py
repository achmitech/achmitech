from odoo.http import request
from odoo.addons.hr_contract_salary_payroll.controllers.main import HrContractSalary as PayrollHrContractSalary


class HrContractSalaryAchmitech(PayrollHrContractSalary):

    def _get_new_version_values(self, version_vals, employee, benefits, offer):
        vals = super()._get_new_version_values(version_vals, employee, benefits, offer)
        vals['client_id'] = offer.client_id.id or False
        vals['mission_order_ref'] = offer.mission_order_ref or False
        return vals

    def _get_compute_results(self, new_version):
        result = super()._get_compute_results(new_version)
        hide_codes = set(
            request.env['hr.contract.salary.resume'].sudo()
            .search([('hide_if_zero', '=', True)])
            .mapped('code')
        )
        if hide_codes:
            for period_lines in result.get('resume_lines_mapped', {}).values():
                for code in list(period_lines.keys()):
                    if code in hide_codes and period_lines[code][1] == 0:
                        del period_lines[code]
        return result
