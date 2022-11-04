from odoo import api, fields, models, _
#from pprint import pprint
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class StockPickingBatch(models.Model):

    _inherit = "stock.picking.batch"
  
    @api.multi
    def set_picked(self):
        self.mapped('move_line_ids').write({'picked': True})
        self.write({'picked': True})

    pick_group_id = fields.Many2one("pick.group", string="Pick Group")
    picked = fields.Boolean('Picked', default=True)


    @api.model
    def get_apk_info(self, values):
        vals = super().get_apk_info(values)
        batch_id = values.get('id', False)
        batch_id = self.browse(batch_id)
        vals['picked'] = batch_id.picked
        return vals

    @api.multi
    def assign_to_new_pick_group(self):
      
        group_id = self.env['pick.group'].assign(self)
        action = self.env.ref("apk_manager_pick_group.action_pick_group_form")
        action["res_id"] = group_id.id
        return action

    @api.multi
    def assign_to_pick_group(self, group_id=False):
        if not self:
            return
        type_id = self[0].picking_type_id
        if not group_id:
            domain = [('picking_type_id.code', '=', type_id.code), ('user_id', '=', False), ('state', '!=', 'picked'), ('picking_type_id.default_location_src_id', '=', type_id.default_location_src_id.id)]
            group_id = self.env['pick.group'].search(domain, limit=1)
        if not group_id:
            return self.env['pick.group'].assign(self)
        for batch in self:
            group_id.fill_with_batch(batch)

    def assign_order_moves(self):
        res = super().assign_order_moves()
        for batch in self:
            if batch.picking_type_id:
                picked = not batch.picking_type_id.need_picking

            batch.move_line_ids.write({'picked': picked})
            
        return res