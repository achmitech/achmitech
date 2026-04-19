# -*- coding: utf-8 -*-

import json
import logging
import re
import secrets
import ssl
import urllib.error
import urllib.request
from urllib.parse import urljoin

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    availability_negotiable = fields.Boolean(string="Négociable", default=False)

    ai_score = fields.Integer(string='Score IA', default=0)
    ai_notes = fields.Text(string='Notes IA')
    ai_recommendation = fields.Selection([
        ('strong_yes', 'Fortement recommandé'),
        ('yes', 'Recommandé'),
        ('maybe', 'À considérer'),
        ('no', 'Non recommandé'),
    ], string='Recommandation IA')
    ai_scoring_status = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Traité'),
        ('error', 'Erreur'),
        ('no_cv', 'Pas de CV'),
    ], string='Statut scoring IA')
    applicant_extracted_json = fields.Text(string='Données extraites (JSON)', readonly=True, copy=False)

    evaluation_ids = fields.One2many(
        comodel_name="hr.applicant.evaluation",
        inverse_name="applicant_id",
        string="Evaluations",
        copy=False,
    )

    dca_access_token = fields.Char(copy=False, index=True)
    applicant_dossier_url = fields.Char("Lien de dossier de candidat", compute="_construct_dossier_url")
    dca_submitted = fields.Boolean(string="Dossier soumis", default=False, tracking=True)
    dca_submitted_date = fields.Datetime(string="Date de soumission", tracking=True)

    # optional but VERY useful for debugging / audit
    dca_payload_json = fields.Text(string="Snapshot dossier (JSON)")

    dossier_experience_ids = fields.One2many(
        "hr.applicant.dossier.experience",
        "applicant_id",
        string="Expériences (Dossier)",
        copy=False,
    )
    
    dossier_formation_ids = fields.One2many(
        "hr.applicant.dossier.formation",
        "applicant_id",
        string="Formations",
    )

    dossier_habilitation_ids = fields.One2many(
        "hr.applicant.dossier.habilitation",
        "applicant_id",
        string="Habilitations",
    )

    @api.depends("dca_access_token", "stage_id")
    def _construct_dossier_url(self):
        for applicant in self:
            if applicant.dca_access_token:
                base_url = applicant.get_base_url()
                applicant.applicant_dossier_url = urljoin(
                    base_url, f"/dossier/{applicant.dca_access_token}"
                )
            else:
                applicant.applicant_dossier_url = False

    def write(self, vals):
        res = super().write(vals)

        if "stage_id" in vals:
            e1 = self.env.ref("hr_recruitment.stage_job0", raise_if_not_found=False)
            if e1:
                for applicant in self:
                    if applicant.stage_id.id == e1.id:
                        # generate only once
                        if not applicant.dca_access_token:
                            applicant.dca_access_token = secrets.token_urlsafe(32)
                        # reset dossier state only once (or on first entry)
                        if applicant.dca_submitted:
                            applicant.dca_submitted = False

        return res
    
    def move_to_new_stage(self):
        # Find the new first stage (sequence = -1)
        new_stage = self.env["hr.recruitment.stage"].search(
            [("sequence", "=", -1)],
            limit=1
        )

        if not new_stage:
            raise UserError("Stage with sequence = -1 not found.")

        # Find the old first stage (sequence = 0)
        old_stage = self.env["hr.recruitment.stage"].search(
            [("sequence", "=", 0)],
            limit=1
        )

        if not old_stage:
            raise UserError("Stage with sequence = 0 not found.")

        # Find all applicants currently in the old stage
        applicants = self.env["hr.applicant"].search([
            ("stage_id", "=", old_stage.id)
        ])

        _logger.info("Number of candidates in old stage is: %s", len(applicants))
        # Move them to the new stage
        applicants.write({
            "stage_id": new_stage.id
        })

        # Optional log
        _logger.info(
            f"Moved {len(applicants)} applicants from stage '{old_stage.name}' "
            f"to new stage '{new_stage.name}'."
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.write({'ai_scoring_status': 'pending'})
        return records

    def action_trigger_ai_scoring(self):
        self._send_to_n8n()

    def _send_to_n8n(self):
        n8n_webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'achmitech_hr_recruitment.n8n_webhook_url'
        )
        if not n8n_webhook_url:
            _logger.error("AI Scoring: paramètre 'achmitech_hr_recruitment.n8n_webhook_url' non configuré")
            return

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for record in self:
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'hr.applicant'),
                ('res_id', '=', record.id),
            ], limit=1)

            if not attachment:
                _logger.warning("AI Scoring: aucun CV trouvé pour le candidat %s, ignoré", record.id)
                continue

            cv_text = attachment.index_content or ''
            job_description = re.sub(r'<[^>]+>', ' ', record.job_id.description or '').strip()

            payload = json.dumps({
                'applicant_id': record.id,
                'applicant_name': record.partner_name or '',
                'job_position': record.job_id.name or '',
                'job_description': job_description,
                'stage': record.stage_id.name or '',
                'cv_text': cv_text,
            }).encode('utf-8')

            try:
                req = urllib.request.Request(
                    n8n_webhook_url,
                    data=payload,
                    headers={'Content-Type': 'application/json'},
                    method='POST',
                )
                urllib.request.urlopen(req, timeout=10, context=ctx)
                record.ai_scoring_status = 'done'
                _logger.info("AI Scoring: candidat %s envoyé à n8n", record.id)
            except urllib.error.URLError as e:
                _logger.error("AI Scoring: échec pour le candidat %s: %s", record.id, str(e))
                record.ai_scoring_status = 'error'

    def _cron_ai_scoring(self):
        pending = self.search([('ai_scoring_status', '=', 'pending')])
        if not pending:
            return
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.applicant'),
            ('res_id', 'in', pending.ids),
        ])
        applicant_ids_with_cv = attachments.mapped('res_id')
        pending.filtered(lambda a: a.id in applicant_ids_with_cv)._send_to_n8n()

    def _get_alten_table_rows_from_experiences(self):
        """
        Returns:
        [
          {"label": "Logiciels", "value": "AutoCAD, QGIS, ..."},
          {"label": "Langages", "value": "Python, Java, ..."},
          ...
        ]

        - skill types are NOT hardcoded
        - rows come from types present in experience competency lines
        - skills deduplicated across experiences (by skill_id)
        - stable ordering by skill type sequence then name (if those fields exist)
        """
        self.ensure_one()

        # type_id -> {"type": record, "skills": ordered dict {skill_id: name}}
        buckets = {}
        type_order = []  # first-seen ordering fallback

        def _ensure_bucket(t):
            if t.id not in buckets:
                buckets[t.id] = {"type": t, "skills": {}}
                type_order.append(t.id)
            return buckets[t.id]

        # collect
        for exp in self.dossier_experience_ids.sorted(lambda r: getattr(r, "sequence", 0)):
            for line in exp.competency_line_ids.sorted(lambda r: getattr(r, "sequence", 0)):
                t = line.skill_type_id
                s = line.skill_id
                if not t or not s:
                    continue
                b = _ensure_bucket(t)
                if s.id not in b["skills"]:
                    b["skills"][s.id] = s.name


        all_types = self.env["hr.skill.type"].search([], order="sequence, name")

        rows = []
        for t in all_types:
            skills = list(buckets.get(t.id, {"skills": {}})["skills"].values())
            rows.append({
                "label": t.display_name,
                "value": ", ".join(skills),   # will be "" if none
            })
        return rows

    