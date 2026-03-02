# -*- coding: utf-8 -*-
import werkzeug.exceptions
from operator import itemgetter
from odoo import http, fields
from odoo.http import request
from odoo.tools import groupby as groupbyelem
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class PortalLeaves(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Only add counter values here — this method is also called by the /my/counters
        JSON-RPC endpoint, which returns the full dict to JavaScript. Any non-counter key
        we add here would cause a JS TypeError when the browser tries to find a DOM element
        with that data-placeholder_count attribute."""
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'pending_leaves_count' in counters:
            values['pending_leaves_count'] = request.env['hr.leave'].sudo().search_count([
                ('client_partner_id', '=', partner.id),
                ('state', '=', 'client_validate'),
            ])
        if 'my_leaves_count' in counters:
            employee = self._get_interim_employee()
            if employee:
                values['my_leaves_count'] = request.env['hr.leave'].sudo().search_count([
                    ('employee_id', '=', employee.id),
                    ('state', 'not in', ['draft', 'cancel']),
                ])
        return values

    def _get_portal_role_flags(self):
        """Compute is_interim / is_client flags for template rendering only.
        Both flags are restricted to portal users — internal users (admin, HR, managers)
        must never see these cards even if they happen to have an hr.employee record."""
        if not request.env.user.has_group('base.group_portal'):
            return False, False
        partner = request.env.user.partner_id
        employee = self._get_interim_employee()
        is_client = request.env['hr.employee'].sudo().search_count([
            ('client_project_id.partner_id', '=', partner.id),
        ]) > 0
        return bool(employee), is_client

    @http.route(['/my', '/my/home'], type='http', auth='user', website=True)
    def home(self, **kw):
        """Override portal home to inject is_interim / is_client and pending count."""
        response = super().home(**kw)
        is_interim, is_client = self._get_portal_role_flags()
        qcontext = {'is_interim': is_interim, 'is_client': is_client}
        if is_client:
            partner = request.env.user.partner_id
            qcontext['pending_leaves_count'] = request.env['hr.leave'].sudo().search_count([
                ('client_partner_id', '=', partner.id),
                ('state', '=', 'client_validate'),
            ])
        response.qcontext.update(qcontext)
        return response

    def _get_client_partner(self):
        return request.env.user.partner_id

    def _get_interim_employee(self):
        return request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

    def _check_leave_access(self, leave_id):
        """Return the leave record, or raise 403 if the current user is not its client."""
        partner = self._get_client_partner()
        leave = request.env['hr.leave'].sudo().browse(leave_id).exists()
        if not leave or leave.client_partner_id.id != partner.id:
            raise werkzeug.exceptions.Forbidden()
        return leave

    # ── List page ─────────────────────────────────────────────────────────────

    _TEAM_LEAVES_STEP = 20

    # Shared sortings used by both the client list and the interim list.
    # Client-specific keys (employee, deadline) are appended below.
    _LEAVES_SORTINGS = {
        'create_desc': {'label': "Date de demande (récent en premier)", 'order': 'create_date desc'},
        'create_asc':  {'label': "Date de demande (ancien en premier)", 'order': 'create_date asc'},
        'start_desc':  {'label': "Date de début (décroissant)",         'order': 'date_from desc'},
        'start_asc':   {'label': "Date de début (croissant)",           'order': 'date_from asc'},
        'type':        {'label': "Type de congé",                       'order': 'holiday_status_id'},
    }

    _TEAM_LEAVES_SORTINGS = {
        **_LEAVES_SORTINGS,
        'employee': {'label': "Intérimaire",       'order': 'employee_id'},
        'deadline': {'label': "Délai de réponse",  'order': 'client_deadline asc'},
    }

    _TEAM_LEAVES_GROUPBY = {
        'none':              {'label': "Aucun"},
        'employee_id':       {'label': "Intérimaire"},
        'holiday_status_id': {'label': "Type de congé"},
    }

    _TEAM_LEAVES_INPUTS = {
        'employee': {'input': 'employee', 'label': "Rechercher par intérimaire"},
        'type':     {'input': 'type',     'label': "Rechercher par type de congé"},
    }

    @http.route(
        ['/my/team-leaves', '/my/team-leaves/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def team_leaves_list(self, page=1, tab='pending', sortby=None, groupby='none',
                         search=None, search_in='employee', **kw):
        partner = self._get_client_partner()
        Leave = request.env['hr.leave'].sudo()

        # ── Always compute pending count for the tab badge ─────────────────
        pending_count = Leave.search_count([
            ('client_partner_id', '=', partner.id),
            ('state', '=', 'client_validate'),
        ])

        # ── Default sort per tab ───────────────────────────────────────────
        if not sortby or sortby not in self._TEAM_LEAVES_SORTINGS:
            sortby = 'create_desc'
        order = self._TEAM_LEAVES_SORTINGS[sortby]['order']
        if groupby != 'none':
            order = f'{groupby}, {order}'

        # ── Base domain for the active tab ─────────────────────────────────
        base_domain = [('client_partner_id', '=', partner.id)]
        if tab == 'pending':
            base_domain += [('state', '=', 'client_validate')]
        else:
            base_domain += [('state', 'in', ['validate', 'refuse'])]

        # ── Search ─────────────────────────────────────────────────────────
        if search:
            if search_in == 'employee':
                base_domain += [('employee_id.name', 'ilike', search)]
            elif search_in == 'type':
                base_domain += [('holiday_status_id.name', 'ilike', search)]

        # ── Pager ──────────────────────────────────────────────────────────
        total = Leave.search_count(base_domain)
        url_args = {
            'tab': tab, 'sortby': sortby, 'groupby': groupby,
            'search_in': search_in, 'search': search or '',
        }
        pager = portal_pager(
            url='/my/team-leaves',
            url_args=url_args,
            total=total,
            page=page,
            step=self._TEAM_LEAVES_STEP,
        )

        # ── Fetch and group records ────────────────────────────────────────
        leaves = Leave.search(
            base_domain, order=order,
            limit=self._TEAM_LEAVES_STEP, offset=pager['offset'],
        )
        if groupby != 'none' and leaves:
            grouped_leaves = [
                Leave.concat(*g)
                for _, g in groupbyelem(leaves, itemgetter(groupby))
            ]
        else:
            grouped_leaves = [leaves]

        flash = request.session.pop('leave_flash', None)
        values = self._prepare_portal_layout_values()
        values.update({
            'grouped_leaves': grouped_leaves,
            'pending_count': pending_count,
            'active_tab': tab,
            'page_name': 'team_leaves',
            'flash': flash,
            'pager': pager,
            'searchbar_sortings': self._TEAM_LEAVES_SORTINGS,
            'searchbar_groupby': self._TEAM_LEAVES_GROUPBY,
            'searchbar_inputs': self._TEAM_LEAVES_INPUTS,
            'sortby': sortby,
            'groupby': groupby,
            'search': search or '',
            'search_in': search_in,
            'default_url': '/my/team-leaves',
            'today': fields.Date.today(),
        })
        return request.render('achmitech_portal_leaves.portal_team_leaves_list', values)

    # ── Detail page ───────────────────────────────────────────────────────────

    @http.route('/my/team-leaves/<int:leave_id>', type='http', auth='user', website=True)
    def team_leave_detail(self, leave_id, **kw):
        leave = self._check_leave_access(leave_id)
        flash = request.session.pop('leave_flash', None)
        values = self._prepare_portal_layout_values()
        values.update({
            'leave': leave,
            'page_name': 'team_leaves',
            'flash': flash,
        })
        return request.render('achmitech_portal_leaves.portal_team_leave_detail', values)

    # ── Approve ───────────────────────────────────────────────────────────────

    @http.route(
        '/my/team-leaves/<int:leave_id>/approve',
        type='http', auth='user', website=True, methods=['POST'],
    )
    def team_leave_approve(self, leave_id, **kw):
        leave = self._check_leave_access(leave_id)
        if leave.state == 'client_validate':
            try:
                leave.action_client_approve()
                request.session['leave_flash'] = {
                    'type': 'success',
                    'message': "Demande de congé approuvée avec succès.",
                }
            except Exception as e:
                request.session['leave_flash'] = {'type': 'danger', 'message': str(e)}
        return request.redirect('/my/team-leaves')

    # ── Refuse ────────────────────────────────────────────────────────────────

    @http.route(
        '/my/team-leaves/<int:leave_id>/refuse',
        type='http', auth='user', website=True, methods=['POST'],
    )
    def team_leave_refuse(self, leave_id, **post):
        leave = self._check_leave_access(leave_id)
        reason = (post.get('reason') or '').strip()
        if leave.state == 'client_validate':
            try:
                leave.action_client_refuse(reason=reason)
                request.session['leave_flash'] = {
                    'type': 'info',
                    'message': "Demande de congé refusée.",
                }
            except Exception as e:
                request.session['leave_flash'] = {'type': 'danger', 'message': str(e)}
        return request.redirect('/my/team-leaves')

    # ════════════════════════════════════════════════════════════════════════
    # Interim-side portal  (/my/leaves)
    # ════════════════════════════════════════════════════════════════════════

    _MY_LEAVES_STEP = 20

    _MY_LEAVES_FILTERBY = {
        'all':        {'label': "Toutes",                 'domain': []},
        'pending':    {'label': "En attente du client",   'domain': [('state', '=', 'client_validate')]},
        'processing': {'label': "En cours de traitement", 'domain': [('state', '=', 'confirm')]},
        'approved':   {'label': "Approuvées",             'domain': [('state', 'in', ['validate', 'validate1'])]},
        'refused':    {'label': "Refusées",               'domain': [('state', '=', 'refuse')]},
    }

    @http.route(['/my/leaves', '/my/leaves/page/<int:page>'], type='http', auth='user', website=True)
    def my_leaves_list(self, page=1, sortby='create_desc', filterby='all', **kw):
        employee = self._get_interim_employee()
        if not employee:
            return request.redirect('/my')

        sortings = self._LEAVES_SORTINGS
        filterby_options = self._MY_LEAVES_FILTERBY

        if sortby not in sortings:
            sortby = 'create_desc'
        if filterby not in filterby_options:
            filterby = 'all'

        order = sortings[sortby]['order']
        filter_domain = filterby_options[filterby]['domain']

        base_domain = [
            ('employee_id', '=', employee.id),
            ('state', 'not in', ['draft', 'cancel']),
        ] + filter_domain

        Leave = request.env['hr.leave'].sudo()
        total = Leave.search_count(base_domain)

        pager = portal_pager(
            url='/my/leaves',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=total,
            page=page,
            step=self._MY_LEAVES_STEP,
        )

        leaves = Leave.search(
            base_domain, order=order,
            limit=self._MY_LEAVES_STEP, offset=pager['offset'],
        )

        # Only show leave types the employee can actually request:
        # - must be part of our client-workflow (approval or notification)
        # - must not require an allocation they don't have
        leave_types = request.env['hr.leave.type'].sudo().with_context(
            employee_id=employee.id,
        ).search([
            '|',
            ('require_client_approval', '=', True),
            ('notify_client_on_confirm', '=', True),
            '|',
            ('requires_allocation', '=', False),
            ('has_valid_allocation', '=', True),
        ])

        flash = request.session.pop('leave_flash', None)
        values = self._prepare_portal_layout_values()
        values.update({
            'employee': employee,
            'allocation_remaining': employee.allocation_remaining_display,
            'allocation_total': employee.allocation_display,
            'leaves': leaves,
            'leave_types': leave_types,
            'page_name': 'my_leaves',
            'flash': flash,
            'pager': pager,
            'sortby': sortby,
            'filterby': filterby,
            'searchbar_sortings': {k: v['label'] for k, v in sortings.items()},
            'searchbar_filters': {k: v['label'] for k, v in filterby_options.items()},
            'default_url': '/my/leaves',
        })
        return request.render('achmitech_portal_leaves.portal_my_leaves_list', values)

    @http.route('/my/leaves/new', type='http', auth='user', website=True, methods=['POST'])
    def my_leave_create(self, **post):
        employee = self._get_interim_employee()
        if not employee:
            return request.redirect('/my')

        leave_type_id = int(post.get('leave_type_id') or 0)
        date_from = post.get('date_from', '').strip()
        date_to = post.get('date_to', '').strip()
        name = (post.get('name') or '').strip()

        if not (leave_type_id and date_from and date_to):
            request.session['leave_flash'] = {
                'type': 'danger',
                'message': "Veuillez remplir tous les champs obligatoires.",
            }
            return request.redirect('/my/leaves')

        if date_to < date_from:
            request.session['leave_flash'] = {
                'type': 'danger',
                'message': "La date de fin ne peut pas être antérieure à la date de début.",
            }
            return request.redirect('/my/leaves')

        try:
            leave_type = request.env['hr.leave.type'].sudo().browse(leave_type_id)
            if not leave_type.exists():
                raise ValueError("Type de congé invalide.")

            with request.env.cr.savepoint():
                request.env['hr.leave'].sudo().with_context(
                    mail_create_nolog=True,
                ).create({
                    'employee_id': employee.id,
                    'holiday_status_id': leave_type_id,
                    'request_date_from': date_from,
                    'request_date_to': date_to,
                    'name': name or False,
                })
            request.session['leave_flash'] = {
                'type': 'success',
                'message': "Demande de congé soumise avec succès.",
            }
        except Exception as e:
            request.session['leave_flash'] = {'type': 'danger', 'message': str(e)}

        return request.redirect('/my/leaves')
