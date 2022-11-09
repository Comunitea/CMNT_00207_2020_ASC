# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"
    

    def _get_domain_for_incoming_qtys(self, location_id=False):
        location_id = location_id or self.env['stock.warehouse'].search([], limit=1)
        domain = [
            ('picking_type_id.code', '=', 'incoming'),
            ('state', 'in', ['assigned', 'partially_available']),
            ('location_dest_id', 'child_of', location_id.id), 
            ('location_id.usage', '=', 'supplier')]
        if self:
            domain += [('product_id', '=', self.id)]
        return domain

    def _get_domain_for_outgoing_qtys(self, location_id=False):
        location_id = location_id or self.env['stock.warehouse'].search([], limit=1)
        domain = [
            ('state', 'in', ['confirmed', 'assigned', 'partially_available']),
            ('location_dest_id.usage', '!=', 'internal'),
            ('picking_id.ready_to_send', '=', True),
            ('location_id', 'child_of', location_id.id)]
        if self:
            domain += [('product_id', '=', self.id)]
        return domain
    
    @api.multi
    def _compute_date_estimated_stock(self):
        ## Disponible, menos lo que hay confirmado - lo que hay pendiente de salir sin entradas
        now = fields.datetime.now()
        ctx = self._context.copy()
        wh_id = self.env['stock.warehouse'].search([], limit=1)
        for product_id in self:
            ctx.update(location=wh_id.lot_stock_id.id)
            outgoing_moves = self.env['stock.move'].search(self._get_domain_for_outgoing_qtys(wh_id.lot_stock_id))
            print(outgoing_moves)
            outgoing_qty = sum(x.product_uom_qty for x in outgoing_moves)

            qty_available = product_id.qty_available - outgoing_qty
            moves = self.env['stock.move'].search(product_id._get_domain_for_incoming_qtys(wh_id.lot_stock_id), order="date_expected asc")
            date_estimated_stock = date_estimated_stock_available = False
            estimated_stock_available = qty_available if qty_available > 0  else 0.00
          
            
            if moves:
                product_id.incoming_vendor_moves = moves
                date_estimated_stock_available = False
                date_estimated_stock = moves[0].date_expected
                if qty_available > 0:
                    print("Tengo cantidad disponible")
                    estimated_stock_available =  moves[0].reserved_availability + qty_available
                else:
                    print("NO Tengo cantidad disponible")
                    qty_available = -qty_available
                    for move in moves:
                        qty = move.reserved_availability
                        if qty > qty_available:
                            date_estimated_stock_available = move.date_expected
                            estimated_stock_available = qty - qty_available
                            break
                        else:
                            qty_available -= qty
            product_id.date_estimated_stock = fields.Date.to_string(date_estimated_stock)
            product_id.date_estimated_stock_available = fields.Date.to_string(date_estimated_stock_available)
            product_id.estimated_stock_available=estimated_stock_available
            product_id.incoming_vendor_moves = moves

    estimated_stock_available = fields.Float("Estimated Stock Available", compute='_compute_date_estimated_stock', help="If stock, then today; else date for the first day qith available stock. False if not incoming qty")
    date_estimated_stock = fields.Date("Date for 1º incoming", compute='_compute_date_estimated_stock', help="Fecha de la primera recepción de mercancía")
    date_estimated_stock_available = fields.Date("Date for available stock", compute='_compute_date_estimated_stock', help="If stock, then today; else date for the first day qith available stock. False if not incoming qty")
    incoming_vendor_moves = fields.One2many('stock.move', string='Receipts', compute='_compute_date_estimated_stock')


    @api.multi
    def open_incoming_moves_view(self):

        product_id = self._context.get('product_id', False)

        tree_view = self.env.ref('product_expected_incoming_date.view_move_tree_incoming')
        action = self.env.ref('stock.stock_move_action').read()[0]
        action['view_id'] =  tree_view.id
        action['views'] = [(tree_view.id, 'tree')]
        action['view_mode'] =  'tree'
        if product_id:
            domain = product_id._get_domain_for_incoming_qtys()
            hide_product = 1
        else:
            domain = self._get_domain_for_incoming_qtys()
            hide_product = 0
        action["domain"] = domain
        action["context"] = {
            'hide_product': hide_product,
            'search_default_done': 0, 
            'search_default_ready': 1,
            'search_default_groupby_location_id': 0
        }
        return action