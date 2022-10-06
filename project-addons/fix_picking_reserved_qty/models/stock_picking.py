# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def fix_reserved_qty(self):
        location_id = self.location_id
        product_id = self.product_id
        lot_id = self.lot_id or False
        qty = self.product_uom_qty
        domain = [
            ('location_id', '=', location_id.id), 
            ('product_id', '=', product_id.id), 
            ('lot_id', '=', lot_id)
        ]
        _logger.info("Borro en bd la línea id: %d. Desde %s: %s"%(self.id, location_id.display_name, product_id.display_name))
        sql = "delete from stock_move_line where id=%d"%self.id
        self._cr.execute(sql)
        self._cr.commit()
        ## Ahora tengo que corregir el quant afectado
        Quant = self.env['stock.quant'].sudo().search(domain)
        Sml_ids = self.env['stock.move.line'].search(domain)
        qty_reserved = 0.00
        for sml in Sml_ids:
            qty_reserved += sml.product_uom_qty
        _logger.info("Quant con reserva %s. En movimientos %s"%(Quant.reserved_quantity, qty_reserved))
        ## Puedo solucionarlo así
        if Quant.reserved_quantity > qty_reserved:
            Quant.reserved_quantity = qty_reserved
            _logger.info("Quant corregido")

        else:
            ## Voy a borrar los movimientos
            _logger.info ("Error persistente en %s para %s"%(location_id.display_name, product_id.display_name))
            
            move_ids = Sml_ids.sorted('create_date').mapped('move_id')
            for sml_id in Sml_ids:
                sql = "delete from stock_move_line where id=%d"%self.id
            self._cr.execute(sql)
            self._cr.commit()
            for move_id in move_ids:
                _logger.info ("Comprobando %s"%move_id.picking_id.name)
                move_id.state = 'partially_available'
                move_id._action_assign()
                _logger.info ("Estado %s"%move_id.picking_id.state)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def fix_picking_reserved_qty(self):
        for pick in self:
            for line in pick.move_line_ids:
                try:
                    line.unlink()
                except:
                    line.fix_reserved_qty()
                        





