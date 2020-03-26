# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = "sale.order"

    perc_margin = fields.Float(
        compute="_product_margin",
        string="Margin (%)",
        help="It gives profitability by calculating the difference between "
             "the Unit Price and the cost in %",
        digits=dp.get_precision("Product Price"),
        store=True,
    )

    @api.depends("order_line.margin", "amount_untaxed")
    def _product_margin(self):
        super()._product_margin()
        for order in self:
            order.perc_margin = (
                order.margin / order.amount_untaxed * 100
                if order.amount_untaxed != 0.00
                else 0
            )
