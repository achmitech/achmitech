from odoo import models, fields

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee"

    cra_order_number = fields.Char(string="N° Commande (CRA)")
