# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    # ── New state ──────────────────────────────────────────────────────────────

    state = fields.Selection(
        selection_add=[('client_validate', 'En attente du client')],
        ondelete={'client_validate': 'set default'},
    )

    # ── Client-related fields ──────────────────────────────────────────────────

    client_partner_id = fields.Many2one(
        'res.partner',
        string="Client",
        compute='_compute_client_partner_id',
        store=True,
        help="Partenaire client déduit du projet mission de l'employé.",
    )
    client_refuse_reason = fields.Char(
        string="Motif de refus client",
        copy=False,
    )
    client_deadline = fields.Date(
        string="Délai de réponse client",
        compute='_compute_client_deadline',
        store=True,
        help="Date limite au-delà de laquelle un rappel automatique est envoyé au client.",
    )
    client_reminded = fields.Boolean(
        string="Rappel envoyé",
        default=False,
        copy=False,
    )

    # ── Computed fields ────────────────────────────────────────────────────────

    @api.depends('employee_id.client_project_id')
    def _compute_client_partner_id(self):
        for leave in self:
            leave.client_partner_id = leave.employee_id.client_project_id.partner_id

    @api.depends('create_date', 'holiday_status_id.client_response_deadline_days')
    def _compute_client_deadline(self):
        for leave in self:
            days = leave.holiday_status_id.client_response_deadline_days
            if leave.create_date and days:
                leave.client_deadline = leave.create_date.date() + timedelta(days=days)
            else:
                leave.client_deadline = False

    # ── State machine override ─────────────────────────────────────────────────

    def _check_approval_update(self, state, raise_if_not_possible=True):
        """Extend native approval checks to handle the client_validate state."""

        # confirm/draft → client_validate: always allowed for system
        if state == 'client_validate':
            for leave in self:
                if leave.state not in ('confirm', 'draft'):
                    if raise_if_not_possible:
                        raise UserError(_(
                            "Impossible de passer en approbation client depuis l'état courant."
                        ))
                    return False
            return True

        # client_validate → validate or refuse: only superuser (portal controller / HR override)
        if state in ('validate', 'refuse'):
            client_val = self.filtered(lambda l: l.state == 'client_validate')
            if client_val:
                if not self.env.su:
                    if raise_if_not_possible:
                        raise UserError(_(
                            "Cette absence est en attente de l'approbation du client. "
                            "Utilisez les boutons de forçage si nécessaire."
                        ))
                    return False
                # Superuser allowed; check remaining leaves normally
                normal = self - client_val
                if normal:
                    return super(HrLeave, normal)._check_approval_update(
                        state, raise_if_not_possible
                    )
                return True

        return super()._check_approval_update(state, raise_if_not_possible)

    # ── create: intercept require_client_approval leaves on submission ─────────

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        for leave in leaves:
            if (
                leave.holiday_status_id.require_client_approval
                and leave.client_partner_id
                and leave.state == 'confirm'
            ):
                leave.write({'state': 'client_validate'})
                leave._send_client_approval_request()
            elif (
                leave.holiday_status_id.notify_client_on_confirm
                and leave.client_partner_id
            ):
                leave._notify_client_of_leave()
        return leaves

    # ── action_approve: safety net if leave is reset to confirm ───────────────

    def action_approve(self, check_state=True):
        """Redirect confirm→validate to confirm→client_validate for approval types."""
        needs_client = self.filtered(
            lambda l: l.holiday_status_id.require_client_approval
            and l.client_partner_id
            and l.state == 'confirm'
        )
        normal = self - needs_client

        if needs_client:
            needs_client.write({'state': 'client_validate'})
            for leave in needs_client:
                leave._send_client_approval_request()

        if normal:
            return super(HrLeave, normal).action_approve(check_state=check_state)
        return True

    # ── action_refuse: allow from client_validate (HR backend) ────────────────

    def action_refuse(self):
        """Allow HR to refuse leaves that are in client_validate state."""
        client_val = self.filtered(lambda l: l.state == 'client_validate')
        if client_val:
            current_employee = self.env.user.employee_id
            client_val.sudo().write({
                'state': 'refuse',
                'second_approver_id': current_employee.id if current_employee else False,
            })
            client_val.sudo().mapped('meeting_id').write({'active': False})

        normal = self - client_val
        if normal:
            return super(HrLeave, normal).action_refuse()
        return True

    # ── Portal action: client approves ────────────────────────────────────────

    def action_client_approve(self):
        """Called from portal when the client approves. Final decision — no HR step after."""
        self.ensure_one()
        if self.state != 'client_validate':
            raise UserError(_("Cette absence n'est pas en attente d'approbation client."))
        # sudo() + leave_fast_create bypass all HR role / double-validation guards
        # (write() checks self.env.user.has_group, not self.env.su, so sudo alone is not enough)
        self.sudo().with_context(leave_fast_create=True)._action_validate(check_state=False)
        self._notify_employee_of_decision(approved=True)

    # ── Portal action: client refuses ─────────────────────────────────────────

    def action_client_refuse(self, reason=''):
        """Called from portal when the client refuses."""
        self.ensure_one()
        if self.state != 'client_validate':
            raise UserError(_("Cette absence n'est pas en attente d'approbation client."))
        self.sudo().write({
            'state': 'refuse',
            'client_refuse_reason': reason,
        })
        self.sudo().mapped('meeting_id').write({'active': False})
        self._notify_employee_of_decision(approved=False, reason=reason)

    # ── HR override actions (backend buttons, manager group only) ─────────────

    def action_hr_force_validate(self):
        """HR force-validates the leave, bypassing client approval."""
        self.sudo().with_context(leave_fast_create=True)._action_validate(check_state=False)

    def action_hr_force_refuse(self):
        """HR force-refuses the leave, bypassing client approval."""
        self.sudo().write({'state': 'refuse'})
        self.sudo().mapped('meeting_id').write({'active': False})

    # ── Notification helpers ──────────────────────────────────────────────────

    def _send_client_approval_request(self):
        template = self.env.ref(
            'achmitech_portal_leaves.mail_template_leave_client_approval',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _notify_client_of_leave(self):
        template = self.env.ref(
            'achmitech_portal_leaves.mail_template_leave_client_notify',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _notify_employee_of_decision(self, approved, reason=''):
        ref = (
            'achmitech_portal_leaves.mail_template_leave_approved_by_client'
            if approved
            else 'achmitech_portal_leaves.mail_template_leave_refused_by_client'
        )
        template = self.env.ref(ref, raise_if_not_found=False)
        if template:
            template.with_context(client_refuse_reason=reason).send_mail(
                self.id, force_send=True
            )

    # ── Cron: send deadline reminders ─────────────────────────────────────────

    @api.model
    def _cron_send_client_leave_reminders(self):
        today = fields.Date.today()
        overdue = self.search([
            ('state', '=', 'client_validate'),
            ('client_deadline', '<=', today),
            ('client_reminded', '=', False),
        ])
        reminder = self.env.ref(
            'achmitech_portal_leaves.mail_template_leave_client_reminder',
            raise_if_not_found=False,
        )
        for leave in overdue:
            if reminder:
                reminder.send_mail(leave.id, force_send=True)
            leave.sudo().write({'client_reminded': True})
