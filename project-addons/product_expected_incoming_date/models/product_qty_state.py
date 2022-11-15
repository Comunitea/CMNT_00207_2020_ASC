# © 2022 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from datetime import datetime, timedelta
from odoo.addons import decimal_precision as dp
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)


class ProductQtyState(models.Model):
    _name = "product.qty.state"

    product_id = fields.Many2one("product.product")
    product_tmpl_id = fields.Many2one("product.template")
    qty_available = fields.Float("Qty available", digits=dp.get_precision('Product Unit of Measure'))
    virtual_available = fields.Float('Forecast Quantity', digits=dp.get_precision('Product Unit of Measure'))
    estimated_stock_available = fields.Float("Estimated Stock Available", help="If stock, then today; else date for the first day qith available stock. False if not incoming qty")
    date_estimated_stock = fields.Date("Date for 1º incoming", help="Fecha de la primera recepción de mercancía")
    date_estimated_stock_available = fields.Date("Date for available stock", help="If stock, then today; else date for the first day qith available stock. False if not incoming qty")
    incoming_vendor_moves = fields.Many2many('stock.move', string='Receipts')
    outgoing_moves = fields.Many2many('stock.move', string='Outgoing')

    
    def update_product_qty_status(self, last_days= 1, product_ids = False):
        domain = []
        if product_ids and last_days == 0:
            pass
        else:
            if product_ids:
                domain += [('product_id', 'in', product_ids.ids)]
            if last_days:
                from_date = fields.Datetime.today() - timedelta(days=last_days)
                domain += [('write_date', '>', from_date)]
            
            p_ids = [x['product_id'][0] for x in self.env['stock.move'].search_read(domain, ['product_id'])]
            product_ids = self.env['product.product'].browse(p_ids)

        vals = product_ids.filtered(lambda x: x.default_on).compute_date_estimated_stock()    
        for product_id in vals.keys():
            obj_id = self.search([('product_id', '=', product_id.id)])
            val = vals[product_id]
            if obj_id:
                obj_id.update(val)
            else:
                val['product_id'] = product_id.id
                val['product_tmpl_id'] = product_id.product_tmpl_id.id
                new_id = obj_id.create(val)
                product_id.product_qty_state_id = new_id
                product_id.product_tmpl_id.product_qty_state_id = new_id


        


