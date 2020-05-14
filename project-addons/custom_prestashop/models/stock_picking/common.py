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
    _inherit = "prestashop.stock.picking.listener"

    def on_tracking_number_added(self, record):
        res = super().on_tracking_number_added(record)
        for binding in record.sale_id.prestashop_bind_ids:
            state = binding.backend_id.sent_state
            record.sale_id.prestashop_state = state
            bind_state = state.prestashop_bind_ids.filtered(
                lambda r: r.backend_id == binding.backend_id
            )
            binding.with_delay().export_sale_state(bind_state.prestashop_id)
        return res

    def on_delivered(self, record):
        for binding in record.sale_id.prestashop_bind_ids:
            state = binding.backend_id.delivered_state
            record.sale_id.prestashop_state = state
            bind_state = state.prestashop_bind_ids.filtered(
                lambda r: r.backend_id == binding.backend_id
            )
            binding.with_delay().export_sale_state(bind_state.prestashop_id)
