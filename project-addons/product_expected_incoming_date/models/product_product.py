# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):

    _inherit = "product.template"

    def action_view_stock_move_lines(self):
        self.ensure_one()
        action = self.env.ref('stock.stock_move_action').read()[0]
        action['domain'] = [('product_id.product_tmpl_id', '=', self.id)]
        action['context'] = {
            'default_groupby_status': 1
        }
        return action

    @api.multi
    def recalc_product_qty_state(self):
        self.env['product.qty.state'].update_product_qty_status(last_days=0,product_ids=self.mapped('product_variant_ids').filtered(lambda x:x.default_on))

    product_qty_state_id = fields.Many2one("product.qty.state", "Qty State")
    estimated_stock_available = fields.Float(related="product_qty_state_id.estimated_stock_available")
    date_estimated_stock = fields.Date(related="product_qty_state_id.date_estimated_stock")
    date_estimated_stock_available = fields.Date(related="product_qty_state_id.date_estimated_stock_available")
    incoming_vendor_moves = fields.Many2many(related="product_qty_state_id.incoming_vendor_moves")


class ProductProduct(models.Model):
    _inherit = "product.product"
    

    def get_domain_for_incoming_qtys(self, location_id=False):
        location_id = location_id or self.env['stock.warehouse'].search([], limit=1)
        domain = [
            ('picking_type_id.code', '=', 'incoming'),
            ('state', 'in', ['assigned', 'partially_available']),
            ('location_dest_id', 'child_of', location_id.id), 
            ('location_id.usage', '=', 'supplier')]
        if self:
            domain += [('product_id', 'in', self.ids)]
        return domain

    def get_domain_for_outgoing_qtys(self, location_id=False):
        location_id = location_id or self.env['stock.warehouse'].search([], limit=1)

        domain = [
            ('state', 'in', ['confirmed', 'assigned', 'partially_available']),
            ('location_dest_id.usage', '!=', 'internal'),
            ('picking_id.ready_to_send', '=', True), ## Ojo con esta línea ....
            ('location_id', 'child_of', location_id.id)]

        if self:
            domain += [('product_id', 'in', self.ids)]
        return domain
    
    @api.multi
    def compute_date_estimated_stock(self):
        
        ## Disponible, menos lo que hay confirmado - lo que hay pendiente de salir sin entradas
        now = fields.datetime.now()
        ctx = self._context.copy()
        wh_id = self.env['stock.warehouse'].search([], limit=1)
        outgoing_moves_all = self.env['stock.move'].search(self.get_domain_for_outgoing_qtys(wh_id.lot_stock_id))
        incoming_moves_all = self.env['stock.move'].search(self.get_domain_for_incoming_qtys(wh_id.lot_stock_id), order="date asc")
        res = {}
        ctx.update(location=wh_id.lot_stock_id.id)
        cont = len(self)
        for product_id in self:
            _logger.info("%d >> Recepciones para %s"%(cont, product_id.display_name))
            cont -= 1
            outgoing_moves = outgoing_moves_all.filtered(lambda x: x.product_id == product_id)
            outgoing_qty = sum(x.product_uom_qty for x in outgoing_moves)
            qty_available = product_id.qty_available - outgoing_qty
            moves = incoming_moves_all.filtered(lambda x: x.product_id == product_id)
            date_estimated_stock = date_estimated_stock_available = False
            estimated_stock_available = qty_available if qty_available > 0  else 0.00
            if moves:
                product_id.incoming_vendor_moves = moves
                date_estimated_stock_available = False
                date_estimated_stock = moves[0].date
                if qty_available > 0:
                    estimated_stock_available =  moves[0].reserved_availability + qty_available
                else:
                    qty_available = -qty_available
                    for move in moves:
                        qty = move.reserved_availability
                        if qty > qty_available:
                            date_estimated_stock_available = move.date
                            estimated_stock_available = qty - qty_available
                            break
                        else:
                            qty_available -= qty
            vals = {
                'qty_available': product_id.qty_available,
                'virtual_available': product_id.virtual_available,
                'date_estimated_stock': fields.Date.to_string(date_estimated_stock),
                'date_estimated_stock_available': fields.Date.to_string(date_estimated_stock_available),
                'estimated_stock_available': estimated_stock_available,
                'outgoing_moves': [(6, 0, outgoing_moves.ids)],
                'orderpoint': True if product_id.orderpoint_ids else False,
                'incoming_vendor_moves': [(6, 0, moves.ids)]}
            res[product_id] = vals
        return res

    product_qty_state_id = fields.Many2one("product.qty.state", "Qty State")
    estimated_stock_available = fields.Float(related="product_qty_state_id.estimated_stock_available")
    date_estimated_stock = fields.Date(related="product_qty_state_id.date_estimated_stock")
    date_estimated_stock_available = fields.Date(related="product_qty_state_id.date_estimated_stock_available")
    incoming_vendor_moves = fields.Many2many(related="product_qty_state_id.incoming_vendor_moves")


    @api.multi
    def open_incoming_moves_view(self):
        product_id = self._context.get('product_id', False)
        tree_view = self.env.ref('product_expected_incoming_date.view_move_tree_incoming')
        action = self.env.ref('stock.stock_move_action').read()[0]
        action['view_id'] = tree_view.id
        action['views'] = [(tree_view.id, 'tree')]
        action['view_mode'] = 'tree'
        if product_id:
            domain = product_id.get_domain_for_incoming_qtys()
            hide_product = 1
        else:
            domain = self.get_domain_for_incoming_qtys()
            hide_product = 0
        action["domain"] = domain
        action["context"] = {
            'hide_product': hide_product,
            'search_default_done': False, 
            'search_default_future': True,
            'search_default_groupby_location_id': False,
            'search_default_groupby_picking_type': True
        }
        return action
    
    def action_view_stock_move_lines(self):
        self.ensure_one()
        action = self.env.ref('stock.stock_move_action').read()[0]
        action['domain'] = [('product_id', '=', self.id)]
        action["context"] = {
            'search_default_done': False, 
            'search_default_future': True,
            'search_default_groupby_status': False,
            'search_default_groupby_picking_type': True
        }
        return action

    @api.multi
    def recalc_product_qty_state(self):
        self.env['product.qty.state'].update_product_qty_status(last_days=0, product_ids=self)
