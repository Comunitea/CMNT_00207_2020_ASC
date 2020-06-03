# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ready_to_send = fields.Boolean()

    @api.multi
    def set_ready_to_send_pick_status(self):
        ready_to_send = self._context.get('ready_to_send', False)
        for order in self.filtered(lambda x: x.state == 'done'):
            picking_ids = order.mapped('order_line').mapped('move_ids').filtered(lambda x: x.picking_type_id.group_code.app_integrated and x.state not in ('done', 'cancel', 'draft')).mapped('picking_id')
            for pick in picking_ids:
                pick.ready_to_send = ready_to_send
            order.ready_to_send = ready_to_send



