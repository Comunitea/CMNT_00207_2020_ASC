# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

BATCH_LIMIT = 25

class PickGroupCompute(models.TransientModel):
    _name = 'pick.group.compute'
    _description = 'Batch Picking Lines To Grouped'

    
    def compute_batch_domain(self):
        return [('picking_type_id.need_picking', '=', True), ('state', '=', 'assigned'), ('pick_group_id', '=', False)]

    def pick_group_calculation(self):
        batch_ids = self.env['stock.picking.batch'].search(self.compute_batch_domain(), order="date desc", limit=BATCH_LIMIT).filtered(lambda x: x.move_line_ids)
        if not batch_ids:
            raise ValidationError(_("Batch to pick not found"))
        
        return self.env['pick.group'].assign(batch_ids)

    def planned_pick_group_generation(self):
        wzd_id = self.env['pick.group.compute'].create({})
        wzd_id.pick_group_calculation(self)
        return True