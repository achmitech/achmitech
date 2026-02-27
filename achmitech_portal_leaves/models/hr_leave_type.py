# -*- coding: utf-8 -*-
from odoo import models, fields


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    require_client_approval = fields.Boolean(
        string="Approbation client requise",
        default=False,
        help="Le client doit approuver cette absence avant qu'elle soit validée. "
             "La décision du client est définitive.",
    )
    notify_client_on_confirm = fields.Boolean(
        string="Notifier le client à la soumission",
        default=False,
        help="Envoyer un email informatif au client lorsque l'employé soumet cette absence. "
             "Le client ne peut pas bloquer ce type de congé (ex: maladie, congé parental).",
    )
    client_response_deadline_days = fields.Integer(
        string="Délai de réponse client (jours)",
        default=3,
        help="Nombre de jours après lesquels un rappel est envoyé automatiquement au client.",
    )
