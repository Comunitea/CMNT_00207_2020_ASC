# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.addons.component.core import Component


class AccountPaymentMode(models.Model):

    _inherit = "account.payment.mode"

    prestashop_name = fields.Char()
    prestashop_module = fields.Char()
    defaullt_sale_invoice_policy = fields.Selection(
        [("order", "Ordered quantities"), ("delivery", "Delivered quantities")]
    )


class PaymentModeBinder(Component):
    _inherit = "account.payment.mode.binder"
    _external_field = "prestashop_module"
