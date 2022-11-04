from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, ValidationError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
    
    picked = fields.Boolean('Picked', default=True)
    pick_group_line_id = fields.Many2one('pick.group.line')



class StockMove(models.Model):
    _inherit = "stock.move"
    
    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        vals['picked'] = self.picking_type_id and not self.picking_type_id.need_picking or True
        return vals