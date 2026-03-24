# -*- coding: utf-8 -*-
from odoo import models, fields


class HrJob(models.Model):
    _inherit = 'hr.job'

    internship_missions = fields.Html(string="Missions de stage")
    internship_supervisor_id = fields.Many2one('hr.employee', string="Responsable de stage", domain=[('active', '=', True)])
