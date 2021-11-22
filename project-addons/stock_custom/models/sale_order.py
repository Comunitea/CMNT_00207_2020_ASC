# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ready_to_send = fields.Boolean()
    picking_policy = fields.Selection(track_visibility='onchange')
    prestashop_cancel_alert = fields.Boolean(default=False)
    sent_prestashop_cancel_alert = fields.Boolean(default=False)

    def toggle_ready_to_send(self):
        for order in self:
            order.with_context(manual_ready_to_send=True).write({"ready_to_send": not order.ready_to_send})

    @api.multi
    def action_cancel(self):
        if self.batches_count > 0 and self.mapped("picking_ids.batch_id.user_id"):
            self.prestashop_cancel_alert = True
            return False

        res = super(SaleOrder, self).action_cancel()
        return res
