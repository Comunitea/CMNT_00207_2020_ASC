# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountPaymentMode(models.Model):

    _inherit = "account.payment.mode"

    prestashop_name = fields.Char()
