# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

from odoo import api, models, fields, _


class StcokPicking(models.Model):
    _inherit = "stock.picking"

    delivery_picking_id = fields.Many2one('stock.picking', string="delivery picking")

    def _update_delivery_picking_values(self, partner_id):
        picking_type_id = self.env.ref(
            'delivery_picking_creator.delivery_picking_type')
        vals = {
                'move_type': 'direct',
                'partner_id': partner_id.id,
                'picking_type_id': picking_type_id.id,
                'location_id': picking_type_id.default_location_src_id.id,
                'location_dest_id': picking_type_id.default_location_dest_id.id
            }
        return vals