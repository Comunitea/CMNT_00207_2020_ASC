# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def create_invoices(self):
        all_orders = self.env["sale.order"].browse(self._context.get("active_ids", []))
        current_company_orders = all_orders.filtered(
            lambda r: not r.team_id.invoice_on_company
        )
        super(
            SaleAdvancePaymentInv,
            self.with_context(active_ids=current_company_orders._ids),
        ).create_invoices()
        change_company_orders = all_orders.filtered(
            lambda r: r.team_id.invoice_on_company
        )
        super(
            SaleAdvancePaymentInv,
            self.sudo().with_context(active_ids=change_company_orders._ids),
        ).create_invoices()
        if self._context.get("open_invoices", False) and current_company_orders:
            return current_company_orders.action_view_invoice()
        return {"type": "ir.actions.act_window_close"}
