# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    client_project_id = fields.Many2one(
        'project.project',
        string="Projet client (mission actuelle)",
        tracking=True,
        help="Le projet client associé à la mission actuelle de l'intérimaire. "
             "Le partenaire du projet est le client qui approuvera les absences.",
    )


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    client_project_id = fields.Many2one(
        'project.project',
        string="Projet client (mission actuelle)",
    )
