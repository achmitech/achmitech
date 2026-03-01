# -*- coding: utf-8 -*-

from odoo.exceptions import UserError

from odoo import models, fields, api, _

class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    staffing_need_id = fields.Many2one(
        "staffing.need",
        string="Besoin en personnel",
        ondelete="set null",
        index=True,
    )

    presented_to_client_date = fields.Datetime(
        string="Date présentation client"
    )

    client_interview_date = fields.Datetime(
        string="Date entretien client"
    )

    client_feedback_date = fields.Datetime(
        string="Date retour client"
    )
    
    client_interview_status = fields.Selection([
        ("pending", "Planifié"),
        ("passed", "Terminé"),
        ("failed", "Annulé"),
        ], string="Statut entretien client", default="pending")
    
    # client_feedback_treated_date = fields.Datetime(
    #     string="Date traitement retour client"
    # )

    rejection_source = fields.Selection([
        ("internal", "Interne (Recruteur)"),
        ("client", "Client"),
        ], string="Source de refus")

    # This field is used for easy access in views, to avoid having to check the stage's is_client_interview flag multiple times
    is_client_interview_stage = fields.Boolean(
        related="stage_id.is_client_interview",
        readonly=True,
    )
    
    pool_added_date = fields.Date(
        string="Date ajout vivier", readonly=True, copy=False
    )

    recontact_log_ids = fields.One2many(
        "okr.recontact.log", "applicant_id", string="Recontacts vivier"
    )
    last_recontact_date = fields.Date(
        string="Dernier recontact",
        compute="_compute_last_recontact_date",
        store=True,
    )

    @api.depends("recontact_log_ids.date")
    def _compute_last_recontact_date(self):
        for rec in self:
            dates = rec.recontact_log_ids.mapped("date")
            rec.last_recontact_date = max(dates) if dates else False

    def action_open_recontact_wizard(self):
        self.ensure_one()
        wizard = self.env["okr.recontact.wizard"].sudo().create({"applicant_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "name": "Enregistrer un recontact",
            "res_model": "okr.recontact.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def reset_applicant(self):
       """ Reset the applicant state to progress """
       super().reset_applicant()
       self.write({'rejection_source': False})

    def action_present_to_client(self):
        """ Action to set the applicant as presented to client """
        for applicant in self:
            if not applicant.staffing_need_id:
                raise UserError("Le candidat doit être lié à un besoin pour être présenté au client.")
            if not applicant.availability:
                raise UserError("La disponibilité du candidat doit être renseignée avant de le présenter au client.")
            applicant.write({
                "presented_to_client_date": fields.Datetime.now(),
            })

    def action_client_interview_done(self):
        self.write({"client_interview_status": "passed"})

    def action_client_interview_cancel(self):
        self.write({"client_interview_status": "failed"})

    @api.model
    def _is_client_interview_stage(self, stage):
        return bool(stage and getattr(stage, "is_client_interview", False))

    def write(self, vals):
        # if stage changes to a client interview stage, ensure pending (but don't overwrite passed/failed)
        if "stage_id" in vals:
            new_stage = self.env["hr.recruitment.stage"].browse(vals["stage_id"])
            if self._is_client_interview_stage(new_stage):
                for rec in self:
                    if rec.client_interview_status == "pending":
                        # already pending => ok
                        continue
                    # If you want to auto-reset always, remove this condition.
                    # Safer default: don't overwrite passed/failed automatically.

        # Capture pool_added_date when applicant is first added to talent pool
        if vals.get("pool_applicant_id"):
            newly_pooled = self.filtered(lambda r: not r.pool_applicant_id)
            already_pooled = self - newly_pooled
            if newly_pooled:
                super(HrApplicant, newly_pooled).write(
                    dict(vals, pool_added_date=fields.Date.context_today(self))
                )
            if already_pooled:
                super(HrApplicant, already_pooled).write(vals)
            return True

        result = super().write(vals)

        # Auto-close staffing needs when all positions are filled
        if "stage_id" in vals:
            new_stage = self.env["hr.recruitment.stage"].browse(vals["stage_id"])
            if new_stage.hired_stage:
                needs = self.mapped("staffing_need_id").filtered(
                    lambda n: n.state == "assigned"
                )
                for need in needs:
                    hired = self.env["hr.applicant"].search_count([
                        ("staffing_need_id", "=", need.id),
                        ("stage_id.hired_stage", "=", True),
                    ])
                    if hired >= need.number_of_positions:
                        need.sudo().action_close()

        return result