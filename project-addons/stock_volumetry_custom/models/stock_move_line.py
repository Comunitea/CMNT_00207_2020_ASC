# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"


    def compute_needed_space_in_destination(self):
        self.ensure_one()
        loc = self.location_dest_id
        if loc.volume:
            if loc.box_id:
                volume_factor = self.product_id.volume_factor / 100
            else:
                volume_factor = 1
            needed_space = volume_factor * self.product_id.volume * self.product_uom_qty
        else:
            needed_space = 0
        return needed_space
            