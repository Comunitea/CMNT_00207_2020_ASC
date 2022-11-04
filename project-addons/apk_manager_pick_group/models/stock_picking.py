from odoo import api, fields, models, _
#from pprint import pprint
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):

    _inherit = "stock.picking"

    @api.multi
    def auto_assign_batch_id(self):
        batch_ids = super().auto_assign_batch_id()
        for batch in batch_ids:
            picked = batch.picking_type_id and not batch.picking_type_id.need_picking or True
            batch.move_line_ids.write({'picked': picked})
        return batch_ids

    def get_new_batch_values(self, picking_name=False):
        res = super().get_new_batch_values(picking_name=picking_name)
        if self.picking_type_id and self.picking_type_id.need_picking:
            res['picked'] = False
        return res