# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_min_qty = fields.Float('Product Min Qty', related="orderpoint_id.product_min_qty")
    product_max_qty = fields.Float('Product Max Qty', related="orderpoint_id.product_max_qty")
    product_qty_multiple = fields.Float('Qty Multiple', related="orderpoint_id.qty_multiple")
    product_qty_available_not_res = fields.Float(string='Quantity On Hand Unreserved', compute='_compute_product_qty_available_not_res')

    @api.depends('product_id')
    def _compute_product_qty_available_not_res(self):
        for line in self:
            line.product_qty_available_not_res = line.product_id.qty_available_not_res
