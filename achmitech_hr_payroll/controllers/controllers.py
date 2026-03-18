import base64
import io
import logging
from concurrent.futures import ThreadPoolExecutor

from PyPDF2 import PdfReader

from odoo.http import request
from odoo.addons.hr_contract_salary.controllers.main import SignContract
from odoo.addons.hr_contract_salary_payroll.controllers.main import HrContractSalary as PayrollHrContractSalary

_logger = logging.getLogger(__name__)

# Width and height of signature boxes (relative to page size, 0.0–1.0).
_SIG_WIDTH    = 0.30
_SIG_HEIGHT   = 0.08
# How far below the detected label text the signature box starts (increase to move down).
_SIG_Y_OFFSET = 0.06


class HrContractSalaryAchmitech(PayrollHrContractSalary):

    def _get_new_version_values(self, version_vals, employee, benefits, offer):
        vals = super()._get_new_version_values(version_vals, employee, benefits, offer)
        vals['client_id'] = offer.client_id.id or False
        vals['mission_order_ref'] = offer.mission_order_ref or False
        for field in offer._INDEMNITY_FIELDS:
            vals[field] = offer[field]
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

    # ------------------------------------------------------------------
    # PDF helpers
    # ------------------------------------------------------------------

    def _render_report_pdf(self, report_xml_id, report_name, res_ids):
        report = request.env.ref(report_xml_id)
        pdf_bytes, _ = report.sudo()._render_qweb_pdf(report_name, res_ids=res_ids)
        return pdf_bytes

    def _count_pdf_pages(self, pdf_bytes):
        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)

    def _find_text_position(self, pdf_bytes, search_texts, from_end=False):
        """
        Find the page number and posY (0.0=top, 1.0=bottom) for each search text
        in the PDF using pdfminer text extraction.

        search_texts: dict {key: text_to_find}
        from_end: if True, iterate pages in reverse (finds last occurrence — use for
                  signature labels that also appear elsewhere in the document body)
        Returns dict: {key: {'page': int (1-based), 'posY': float}}
        """
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextBox

        pages = list(extract_pages(io.BytesIO(pdf_bytes)))
        if from_end:
            pages = list(reversed(list(enumerate(pages, start=1))))
        else:
            pages = list(enumerate(pages, start=1))

        results = {}
        remaining = dict(search_texts)

        for page_num, page_layout in pages:
            if not remaining:
                break
            page_height = page_layout.height
            for element in page_layout:
                if not isinstance(element, LTTextBox):
                    continue
                text = element.get_text().strip()
                for key, needle in list(remaining.items()):
                    if needle in text:
                        posY = round(1.0 - (element.y0 / page_height), 4)
                        results[key] = {'page': page_num, 'posY': posY}
                        del remaining[key]

        for key in remaining:
            _logger.warning("Text not found in PDF for key '%s' ('%s')", key, search_texts[key])
        return results

    # ------------------------------------------------------------------
    # Sign template generation
    # ------------------------------------------------------------------

    def _get_sign_roles(self, sign_req):
        """
        Extract employee and employer roles from the sign request items
        (populated by hr.contract.signatory configuration on the offer).
        Returns (employee_role, employer_role) — either may be None.
        """
        employee_role = employer_role = None
        employee_xml_id = 'hr_sign.sign_item_role_employee_signatory'
        try:
            employee_xml_role = request.env.ref(employee_xml_id)
        except Exception:
            employee_xml_role = None

        for item in sign_req.request_item_ids:
            if employee_xml_role and item.role_id == employee_xml_role:
                employee_role = item.role_id
            else:
                employer_role = item.role_id

        # Fallback: assign by order if role matching failed
        items = sign_req.request_item_ids
        if not employee_role and len(items) >= 1:
            employee_role = items[0].role_id
        if not employer_role and len(items) >= 2:
            employer_role = items[1].role_id

        return employee_role, employer_role

    def _create_sign_items(self, document, sig_page, employee_role, employer_role, sig_type,
                           employee_pos, employer_pos):
        """
        Create two signature items on sig_page.
        employee_pos / employer_pos: dicts with posX, posY, width, height (0.0–1.0).
        """
        base = {'document_id': document.id, 'type_id': sig_type.id, 'required': True,
                'page': sig_page}
        request.env['sign.item'].sudo().create([
            {**base, 'responsible_id': employee_role.id, **employee_pos},
            {**base, 'responsible_id': employer_role.id, **employer_pos},
        ])

    def _create_initials_items(self, document, num_pages, employee_role, employer_role, init_type):
        """Add initials sign items at the bottom of every page (left=employer, right=employee)."""
        vals = []
        base = {'document_id': document.id, 'type_id': init_type.id, 'required': True,
                'width': 0.08, 'height': 0.04, 'posY': 0.96}
        for page in range(1, num_pages + 1):
            vals.append({**base, 'responsible_id': employer_role.id, 'page': page, 'posX': 0.02})
            vals.append({**base, 'responsible_id': employee_role.id, 'page': page, 'posX': 0.90})
        request.env['sign.item'].sudo().create(vals)

    def _build_contract_sign_template(self, new_version, sign_req):
        """
        For each document configured on the version's contract type, render the QWeb
        PDF, create one sign.template with one sign.document per file, and add
        signature + initials items using the label texts configured per document.
        """
        sign_docs_config = new_version.contract_type_id.sign_document_ids
        if not sign_docs_config:
            _logger.warning(
                "No sign documents configured on contract type '%s' — skipping template generation",
                new_version.contract_type_id.name,
            )
            return None

        employee_name = new_version.employee_id.name or str(new_version.id)

        # Render all PDFs sequentially (wkhtmltopdf needs HTTP context)
        rendered = []
        for doc_cfg in sign_docs_config:
            pdf_bytes = self._render_report_pdf(
                doc_cfg.report_id.xml_id,
                doc_cfg.report_id.report_name,
                new_version.ids,
            )
            rendered.append((doc_cfg, pdf_bytes))

        # Locate signature zones in parallel via pdfminer (pure Python, no DB)
        futures = {}
        with ThreadPoolExecutor(max_workers=len(rendered)) as pool:
            for doc_cfg, pdf_bytes in rendered:
                f = pool.submit(self._find_text_position, pdf_bytes,
                    {'employee': doc_cfg.employee_label, 'employer': doc_cfg.employer_label}, True)
                futures[doc_cfg.id] = (f, pdf_bytes)

        positions = {cid: (fut.result(), pb) for cid, (fut, pb) in futures.items()}
        _logger.info("Signature positions: %s", {cid: pos for cid, (pos, _) in positions.items()})

        # Build attachment list for sign.template
        attachments = [
            {
                'name': f'{doc_cfg.report_id.name} — {employee_name}.pdf',
                'datas': base64.b64encode(pdf_bytes).decode(),
            }
            for doc_cfg, pdf_bytes in rendered
        ]
        template_data = request.env['sign.template'].sudo().create_from_attachment_data(
            attachments, active=True)
        new_template = request.env['sign.template'].sudo().browse(template_data['id'])

        employee_role, employer_role = self._get_sign_roles(sign_req)
        sig_type = request.env['sign.item.type'].sudo().search(
            [('item_type', '=', 'signature')], limit=1)
        init_type = request.env['sign.item.type'].sudo().search(
            [('item_type', '=', 'initial')], limit=1)

        if not employee_role or not employer_role:
            _logger.warning("Could not resolve both sign roles — skipping sign items")
        elif not sig_type:
            _logger.warning("No signature item type found — skipping sign items")
        else:
            for doc_cfg, pdf_bytes in rendered:
                pos, _ = positions[doc_cfg.id]
                report_name = doc_cfg.report_id.name
                doc = new_template.document_ids.filtered(
                    lambda d, n=report_name: n in d.name)[:1]
                if not doc:
                    _logger.warning("Document not found in template for report '%s'", report_name)
                    continue
                if 'employee' not in pos or 'employer' not in pos:
                    _logger.warning("Signature labels not found in PDF for '%s'", report_name)
                    continue
                self._create_sign_items(
                    doc, pos['employee']['page'], employee_role, employer_role, sig_type,
                    employee_pos={'posX': 0.55, 'posY': pos['employee']['posY'] + _SIG_Y_OFFSET,
                                  'width': _SIG_WIDTH, 'height': _SIG_HEIGHT},
                    employer_pos={'posX': 0.05, 'posY': pos['employer']['posY'] + _SIG_Y_OFFSET,
                                  'width': _SIG_WIDTH, 'height': _SIG_HEIGHT},
                )
                if init_type:
                    self._create_initials_items(doc, self._count_pdf_pages(pdf_bytes),
                                                employee_role, employer_role, init_type)

        return new_template

    # ------------------------------------------------------------------
    # Submit override
    # ------------------------------------------------------------------

    def submit(self, offer_id=None, benefits=None, **kw):
        result = super().submit(offer_id=offer_id, benefits=benefits, **kw)

        if not isinstance(result, dict) or result.get('error') or not result.get('request_id'):
            return result

        try:
            new_version = request.env['hr.version'].sudo().browse(result['new_version_id'])
            sign_req   = request.env['sign.request'].sudo().browse(result['request_id'])

            # Ensure sex is set on new_version before PDF rendering.
            # _update_personal_info writes sex via employee.sex (related to
            # current_version_id.sex), which may point to a different version
            # when the employee already has a future-dated contract.
            if not new_version.sex and isinstance(benefits, dict):
                sex = (benefits.get('employee') or {}).get('sex') or \
                      (benefits.get('version_personal') or {}).get('sex')
                if sex:
                    new_version.write({'sex': sex})

            new_template = self._build_contract_sign_template(new_version, sign_req)
            if not new_template:
                return result
            sign_req.write({'template_id': new_template.id})

            _logger.info(
                "Sign request %s → merged template %s for offer %s",
                sign_req.id, new_template.id, offer_id,
            )
        except Exception:
            _logger.exception(
                "Failed to build contract sign template for offer %s — keeping original",
                offer_id,
            )

        return result


class AchmitechSignContract(SignContract):
    """Patch the sign() flow so that our dynamically-generated CDI+OM template
    is treated as a valid salary-package document by hr_contract_salary."""

    def sign(self, sign_request_id, token, sms_token=False, signature=None, **kwargs):
        req_item = request.env['sign.request.item'].sudo().search(
            [('access_token', '=', token)], limit=1)

        orig_template_id = None
        version = None

        if req_item:
            sr = req_item.sign_request_id
            version = request.env['hr.version'].sudo().search([
                ('sign_request_ids', 'in', sr.ids),
                '|', ('active', '=', True), ('active', '=', False),
            ], limit=1)
            if version and sr.template_id and sr.template_id.id not in [
                version.sign_template_id.id, version.contract_update_template_id.id
            ]:
                orig_template_id = version.sign_template_id.id
                request.env.cr.execute(
                    "UPDATE hr_version SET sign_template_id = %s WHERE id = %s",
                    (sr.template_id.id, version.id),
                )
                request.env.invalidate_all()
                _logger.info(
                    "sign() patched sign_template_id %s → %s for version %s",
                    orig_template_id, sr.template_id.id, version.id,
                )

        result = super().sign(sign_request_id, token, sms_token=sms_token, signature=signature, **kwargs)

        if orig_template_id and version:
            request.env.cr.execute(
                "UPDATE hr_version SET sign_template_id = %s WHERE id = %s",
                (orig_template_id, version.id),
            )
            request.env.invalidate_all()

        return result
