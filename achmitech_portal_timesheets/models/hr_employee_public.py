from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    cra_order_number = fields.Char(string="N° Commande")