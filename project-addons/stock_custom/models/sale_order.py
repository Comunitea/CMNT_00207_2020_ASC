# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ready_to_send = fields.Boolean()

    def toggle_ready_to_send(self):
        for order in self:
            order.write({"ready_to_send": not order.ready_to_send})
