# -*- coding: utf-8 -*-
import base64
from io import BytesIO

import PyPDF2

from odoo import models
from odoo.exceptions import UserError


class HrContractSalaryOffer(models.Model):
    _inherit = 'hr.contract.salary.offer'

    def action_preview_offer_documents(self):
        """Render all sign documents configured on the contract type using the
        contract template version, merge them into one PDF, and return a download
        action.  This lets HR verify the exact output before sending the offer.
        """
        self.ensure_one()
        template = self.contract_template_id
        if not template:
            raise UserError("Aucun modèle de contrat sélectionné sur cette offre.")

        sign_docs = template.contract_type_id.sign_document_ids.sorted('sequence')
        if not sign_docs:
            raise UserError(
                "Aucun document de signature configuré pour le type de contrat « %s »."
                % template.contract_type_id.name
            )

        # Patch the template with this offer's actual values so the preview
        # shows the real salary, job, dates, and allowances instead of blanks.
        # A savepoint ensures the template record is restored after rendering.
        employee = self.employee_id
        patch = {
            'job_id': self.employee_job_id.id or False,
            'contract_date_start': self.contract_start_date or False,
            'contract_date_end': self.contract_end_date or False,
            'wage': self.monthly_wage or 0.0,
            'client_id': self.client_id.id or False,
            'mission_order_ref': self.mission_order_ref or False,
            'l10n_ma_transport_exemption': self.l10n_ma_transport_exemption or 0.0,
            'l10n_ma_meal_allowance': self.l10n_ma_meal_allowance or 0.0,
            'l10n_ma_phone_allowance': self.l10n_ma_phone_allowance or 0.0,
            'l10n_ma_kilometric_exemption': self.l10n_ma_kilometric_exemption or 0.0,
            # sex drives the civility (Monsieur/Madame) — safe to patch, no overlap check
            'sex': employee.sex or False,
        }

        Report = self.env['ir.actions.report']

        # Render all documents inside a savepoint so the template write is
        # always rolled back — the template record must stay unchanged.
        merger = PyPDF2.PdfMerger()
        with self.env.cr.savepoint():
            # sync_contract_dates=True bypasses hr.version's date-sync override
            # so dates are written directly without trying to propagate to
            # sibling versions (which would fail silently on template records
            # that have no employee_id).
            template.with_context(sync_contract_dates=True).write(patch)
            for doc_cfg in sign_docs:
                pdf_bytes, _ = Report._render_qweb_pdf(
                    doc_cfg.report_id.report_name, res_ids=template.ids)
                merger.append(BytesIO(pdf_bytes))

        output = BytesIO()
        merger.write(output)
        merger.close()

        candidate_name = (
            self.applicant_id.partner_name
            or (self.employee_id.name if self.employee_id else None)
            or str(self.id)
        )
        attachment = self.env['ir.attachment'].sudo().create({
            'name': "Aperçu — %s.pdf" % candidate_name,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue()).decode(),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'new',
        }
