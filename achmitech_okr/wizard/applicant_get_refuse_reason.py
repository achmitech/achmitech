from odoo import api, fields, models

class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'
    
    rejection_source = fields.Selection([
        ("internal", "Interne (Recruiteur)"),
        ("client", "Client"),
    ], default="internal", string="Source du refus", required=True)

    def action_refuse_reason_apply(self):
        res = super().action_refuse_reason_apply()

        # Apply to refused applications + duplicates (if any)
        applicants = self.applicant_ids
        if getattr(self, "duplicates_count", 0) and getattr(self, "duplicates", False):
            applicants |= self.duplicate_applicant_ids

        applicants.write({
            "rejection_source": self.rejection_source,
        })
        return res