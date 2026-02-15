# report/report_alten.py
from odoo import api, models

class ReportAlten(models.AbstractModel):
    _name = "report.achmitech_hr_recruitment.print_report_alten"
    _description = "ALTEN Dossier Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["hr.applicant"].browse(docids)

        return {
            "docs": docs,
            "get_rows": lambda a: a._get_alten_table_rows_from_experiences(),
        }
