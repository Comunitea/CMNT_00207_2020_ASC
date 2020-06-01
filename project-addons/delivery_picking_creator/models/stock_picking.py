# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class StcokPicking(models.Model):
    _inherit = "stock.picking"

    delivery_picking_id = fields.Many2one("stock.picking", string="delivery picking")

    def _update_delivery_picking_values(self, partner_id, carrier_id):
        picking_type_id = self.env.ref("delivery_picking_creator.delivery_picking_type")
        vals = {
            "move_type": "direct",
            "partner_id": partner_id.id,
            "carrier_id": carrier_id.id,
            "picking_type_id": picking_type_id.id,
            "location_id": picking_type_id.default_location_src_id.id,
            "location_dest_id": picking_type_id.default_location_dest_id.id,
        }
        return vals
