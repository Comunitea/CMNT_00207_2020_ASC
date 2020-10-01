# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    needs_signature = fields.Boolean(
        related="carrier_id.needs_signature", readonly=True, store=True
    )
    batches_count = fields.Integer(compute="_compute_batches_count")
    paid_shipping_batch_id = fields.Many2one(
        'stock.picking.batch',
        readonly=True
    )

    def _compute_batches_count(self):
        for sale in self:
            sale.batches_count = len(self.mapped("picking_ids.batch_id"))

    def action_view_batch_picking(self):
        batches = self.mapped("picking_ids.batch_id")
        action = self.env.ref(
            "stock_picking_batch_extended.action_stock_batch_picking_tree"
        ).read()[0]
        if len(batches) > 1:
            action["domain"] = [("id", "in", batches.ids)]
        elif len(batches) == 1:
            form_view = [
                (
                    self.env.ref(
                        "stock_picking_batch_extended.stock_batch_picking_form"
                    ).id,
                    "form",
                )
            ]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = batches.ids[0]
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action
