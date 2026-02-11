# -*- coding: utf-8 -*-

import secrets
from urllib.parse import urljoin
from odoo.exceptions import UserError

from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)

class HrApplicant(models.Model):
    _inherit = "hr.applicant"

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
            _logger.info("XXXXXXXXXXXXXXXXXXXX stqge of applicant currently is : %s", applicant.stage_id.name)

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
