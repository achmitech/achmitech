from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    cra_order_number = fields.Char(string="N° Commande")
