# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models
from odoo.addons.component.core import Component


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if vals.get("delivered"):
            for record in self:
                self._event("on_delivered").notify(record)
        return res


class PrestashopStockPickingListener(Component):
    _name = "prestashop.stock.picking.listener"
    _inherit = "base.event.listener"
    _apply_on = ["stock.picking"]

    def on_tracking_number_added(self, record):
        res = super().on_tracking_number_added(record)
        for binding in record.sale_id.prestashop_bind_ids:
            state = binding.backend_id.sent_state
            bind_state = state.prestashp_bind_ids.filtered(
                lambda r: r.backend_id == binding.backend_id
            )
            rel_binder = self.binder_for("sale.order.state.exporter")
            rel_binder.to_external(bind_state)
            binding.with_delay().export_order_state(
                rel_binder.to_external(bind_state)
            )
        return res

    def on_delivered(self, record):
        for binding in record.sale_id.prestashop_bind_ids:
            state = binding.backend_id.delivered_state
            bind_state = state.prestashp_bind_ids.filtered(
                lambda r: r.backend_id == binding.backend_id
            )
            rel_binder = self.binder_for("sale.order.state.exporter")
            rel_binder.to_external(bind_state)
            binding.with_delay().export_order_state(
                rel_binder.to_external(bind_state)
            )
