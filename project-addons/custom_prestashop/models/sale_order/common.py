# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models
from odoo.addons.queue_job.job import job, related_action


class SaleOrder(models.Model):

    _inherit = "sale.order"

    @api.onchange("payment_mode_id")
    def onchange_payment_mode_id(self):
        if (
            self.payment_mode_id
            and self.payment_mode_id.defaullt_sale_invoice_policy
        ):
            self.invoice_policy = (
                self.payment_mode_id.defaullt_sale_invoice_policy
            )

    def write(self, vals):
        res = super().write(vals)
        for order in self:
            if vals.get("prestashop_state"):
                state = order.prestashop_state
                if state.trigger_cancel:
                    order.invoice_ids.filtered(
                        lambda r: r.state == "draft"
                    ).action_cancel()
                    if order.state == "done":
                        order.action_unlock()
                    order.action_cancel()
                elif state.trigger_paid:
                    order.picking_ids.write({"ready_to_send": True})
        return res


class PrestashopSaleOrder(models.Model):
    _inherit = "prestashop.sale.order"

    @api.multi
    def write(self, vals):
        can_edit = True
        if (
            "prestashop_order_line_ids" in vals
            and vals["prestashop_order_line_ids"]
        ):
            for picking in self.odoo_id.picking_ids:
                if picking.state in ("assigned", "done"):
                    can_edit = False
            if not can_edit:
                raise Exception("No se puede editar el pedido.")
            self.odoo_id.picking_ids.filtered(
                lambda r: r.state == "confirmed"
            ).action_cancel()
            if self.odoo_id.state == "done":
                self.odoo_id.action_unlock()
            self.odoo_id.action_cancel()
        res = super().write(vals)
        if (
            "prestashop_order_line_ids" in vals
            and vals["prestashop_order_line_ids"]
            and can_edit
        ):
            self.odoo_id.action_draft()
            self.odoo_id.action_confirm()
        return res
