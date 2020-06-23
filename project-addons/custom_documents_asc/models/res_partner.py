# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_mail = fields.Char(string='Invoice E-mail', help='E-mail used to send the partner invoices.')