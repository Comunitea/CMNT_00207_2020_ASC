# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _



class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"


    
    @api.multi
    def compute_difficulty(self):
        for batch in self:
            volume = 0.0
            weight = 0.0
            lines = 0
            items = 0
            for pick in batch.picking_ids:
                volume += pick.volume
                weight += pick.weight
                items += pick.items
                lines += pick.lines
            batch.volume = volume
            batch.weight = weight
            batch.nitems = items
            batch.nlines = lines

    volume = fields.Float("Volumen", compute="compute_difficulty", digits=(16, 5))
    weight = fields.Float("Weight", compute="compute_difficulty")
    nlines = fields.Integer("Nº lines", compute="compute_difficulty")
    nitems = fields.Integer("Nº items", compute="compute_difficulty")

    def compute_needed_space_in_destination(self):
        self.ensure_one()
        needed_space = 0.00
        for sml in self.move_line_ids:
            loc = sml.location_dest_id
            if loc.volume:
                if loc.box_id:
                    volume_factor = sml.product_id.volume_factor / 100
                else:
                    volume_factor = 1
                needed_space += volume_factor * sml.product_id.volume * sml.product_uom_qty
        
        return needed_space
    
    
