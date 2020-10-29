# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api

import logging

_logger = logging.getLogger(__name__)


class ProductProduct (models.Model):
    _inherit = 'product.product'

    @api.multi
    def compute_reservations(self):
        self.ensure_one()
        warehouse_id = self._context.get(('warehouse_id'), False)
        if not warehouse_id:
            warehouse_id = self.env['stock.warehouse'].search([], limit=1)
        else:
            warehouse_id = self.env['stock.warehouse'].browse(warehouse_id)
        loc_id = warehouse_id.lot_stock_id
        domain = [('location_id', 'child_of', loc_id.id),
                  ('product_id', '=', self.id),
                  ('state', 'in', ('partially_available', 'assigned'))]
        reservations_ids = self.env['stock.move.line'].search(domain)
        self.quantity_reserved_link = sum(x.product_uom_qty for x in reservations_ids)
        domain = [('location_id', 'child_of', loc_id.id),
                  ('product_id', '=', self.id),
                  ('reserved_quantity', '!=', 0)]
        quant_ids = self.env['stock.quant'].search(domain)
        self.quantity_reserved = sum(x.reserved_quantity for x in quant_ids)


    def action_view_stock_moves_reservations(self):
        self.ensure_one()
        warehouse_id = self._context.get(('warehouse_id'), False)
        if not warehouse_id:
            warehouse_id = self.env['stock.warehouse'].search([], limit=1)
        else:
            warehouse_id = self.env['stock.warehouse'].browse(warehouse_id)
        loc_id = warehouse_id.lot_stock_id
        action = self.env.ref('stock.stock_move_line_action').read()[0]
        action['domain'] = [
            ('state', 'in', ['assigned', 'partially_available']),
            ('product_id', '=', self.id),
            ('location_id', 'child_of', loc_id.id),
        ]
        action['context'] = {'search_default_todo': 1}
        action['view_id'] = self.env.ref('quant_picking_rel.view_move_line_quant_link').id
        action['views'][0] = (action['view_id'], 'tree')
        return action

    quantity_reserved_link = fields.Float('Cantidad reservada (Movimientos)', compute="compute_reservations")
    quantity_reserved = fields.Float('Cantidad reservada (Quants)', compute="compute_reservations")