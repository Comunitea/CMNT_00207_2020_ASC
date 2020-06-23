# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ready_to_send = fields.Boolean(string="PDA Ready", default=True)

    @api.depends('ready_to_send', 'move_type', 'move_lines.state', 'move_lines.picking_id')
    @api.one
    def _compute_state(self):
        super()._compute_state()
        if self.state == 'assigned' \
                and not self.ready_to_send \
                and self.picking_type_id.code == 'outgoing' \
                and self.picking_type_id.group_code.app_integrated:
            self.state = 'waiting'


    @api.multi
    def _create_backorder(self, backorder_moves=None):
        backorder = super()._create_backorder(backorder_moves=backorder_moves)
        backorder.write({'move_type': 'one'})
        return backorder
