# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StaffingTransferWizard(models.TransientModel):
    _name = "staffing.transfer.wizard"
    _description = "Assistant de transfert de besoins"

    source_plan_id = fields.Many2one("staffing.plan", string="Plan source", required=True, readonly=True)
    target_plan_id = fields.Many2one(
        "staffing.plan",
        string="Plan cible",
        domain="[('id', '!=', source_plan_id), ('company_id', '=', source_company_id)]",
    )
    source_company_id = fields.Many2one(related="source_plan_id.company_id")
    line_ids = fields.One2many("staffing.transfer.wizard.line", "wizard_id", string="Besoins")

    def action_confirm(self):
        self.ensure_one()
        if not self.target_plan_id:
            raise UserError(_("Veuillez sélectionner un plan cible."))
        lines = self.line_ids.filtered(lambda l: l.selected and l.remaining_positions > 0)
        if not lines:
            raise UserError(_("Aucun besoin sélectionné avec des postes restants."))

        lines.mapped("need_id").write({"staffing_plan_id": self.target_plan_id.id})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Transfert effectué"),
                "message": _("%d besoin(s) transféré(s) vers %s.") % (len(lines), self.target_plan_id.name),
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class StaffingTransferWizardLine(models.TransientModel):
    _name = "staffing.transfer.wizard.line"
    _description = "Ligne de transfert de besoin"

    wizard_id = fields.Many2one("staffing.transfer.wizard", required=True, ondelete="cascade")
    need_id = fields.Many2one("staffing.need", required=True, readonly=True)
    selected = fields.Boolean(default=True)

    name = fields.Char(related="need_id.name", readonly=True)
    partner_id = fields.Many2one(related="need_id.partner_id", readonly=True)
    number_of_positions = fields.Integer(related="need_id.number_of_positions", readonly=True, string="Total")
    positions_filled = fields.Integer(related="need_id.positions_filled", readonly=True, string="Pourvus")
    remaining_positions = fields.Integer(
        string="À transférer",
        compute="_compute_remaining",
    )

    @api.depends("need_id.number_of_positions", "need_id.positions_filled")
    def _compute_remaining(self):
        for line in self:
            line.remaining_positions = line.need_id.number_of_positions - line.need_id.positions_filled
