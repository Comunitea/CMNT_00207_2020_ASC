# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _


class StockLocation(models.Model):
    _inherit = "stock.location"

    def compute_available_volume(self):
        for loc in self:
            if loc.volume:
                ocuppied = 0.00
                for quant in loc.quant_ids:
                    ocuppied += quant.product_id.volume * quant.quantity
                loc.volume_available = loc.volume_factor * ocuppied / loc.volume
            else: 
                loc.volume_available = 1
    
    height = fields.Float("Height", default=100, help="The location height in cm")
    length = fields.Float("Lenght", default=100, help="The location Lenght in cm")
    width = fields.Float("Width", default=100, help="The location width in cm")
    volume = fields.Float("Volume", default=1, help="the location volume in m3", digits=(16, 5))
    has_volumetry = fields.Boolean("Has volumetry", default=True)
    volume_factor = fields.Float("% Available for Products", default=80)
    volume_available = fields.Float("Available volume", compute="compute_available_volume")

    @api.onchange('height', 'width', 'length')
    def compute_location_volume(self):
        for loc in self:
            if loc.has_volumetry:
                loc.volume = loc.height * loc.length * loc.width / 1000000
            else:
                loc.volume = 0.00
