# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    recruitment_dashboard_refresh_interval = fields.Integer(
        related='company_id.recruitment_dashboard_refresh_interval',
        readonly=False,
        string="Intervalle de Rafraîchissement du Dashboard (secondes)",
        help="Intervalle en secondes pour rafraîchir automatiquement le tableau de bord"
    )

    recruitment_show_top_jobs_count = fields.Integer(
        related='company_id.recruitment_show_top_jobs_count',
        readonly=False,
        string="Nombre de Postes à Afficher",
        help="Nombre de postes à afficher dans la section 'Top Postes'"
    )

    recruitment_enable_notifications = fields.Boolean(
        related='company_id.recruitment_enable_notifications',
        readonly=False,
        string="Activer les Notifications du Dashboard"
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    recruitment_dashboard_refresh_interval = fields.Integer(
        default=60,
        string="Intervalle de Rafraîchissement",
        help="Intervalle en secondes pour rafraîchir le dashboard"
    )

    recruitment_show_top_jobs_count = fields.Integer(
        default=5,
        string="Nombre de Postes à Afficher"
    )

    recruitment_enable_notifications = fields.Boolean(
        default=True,
        string="Activer les Notifications"
    )
