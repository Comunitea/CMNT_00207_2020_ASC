# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, _
from odoo.addons.queue_job.job import job, related_action


class SaleOrder(models.Model):

    _inherit = "sale.order"

    ready_to_send = fields.Boolean()

    @api.onchange("payment_mode_id")
    def onchange_payment_mode_id(self):
        if self.payment_mode_id and self.payment_mode_id.defaullt_sale_invoice_policy:
            self.invoice_policy = self.payment_mode_id.defaullt_sale_invoice_policy

    def _create_delivery_line(self, carrier, price_unit):
        return super(SaleOrder, self.with_context(purchase_price=price_unit))._create_delivery_line(carrier, price_unit)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.prestashop_state.trigger_paid:
            res.ready_to_send = True
        return res

    @api.multi
    def action_confirm(self):
        return super(SaleOrder, self.with_context(bypass_risk=True)).action_confirm()

    def check_risk_exception(self):
        partner = self.partner_id.commercial_partner_id
        exception_msg = ""
        if partner.risk_exception:
            exception_msg = _("Financial risk exceeded.\n")
        elif partner.risk_sale_order_limit and (
            (partner.risk_sale_order + self.amount_total)
            > partner.risk_sale_order_limit
        ):
            exception_msg = _("This sale order exceeds the sales orders risk.\n")
        elif partner.risk_sale_order_include and (
            (partner.risk_total + self.amount_total) > partner.credit_limit
        ):
            exception_msg = _("This sale order exceeds the financial risk.\n")
        if exception_msg:
            return True
        return False

    @api.multi
    def _action_confirm(self):
        res = super()._action_confirm()
        for order in self:
            if order.ready_to_send and order.picking_ids:
                order.picking_ids.write({"ready_to_send": True})
        return res

    def write(self, vals):
        res = super().write(vals)
        for order in self:
            if vals.get("prestashop_state"):
                state = order.prestashop_state
                if state.trigger_paid:
                    order.ready_to_send = True
                    order.picking_ids.write({"ready_to_send": True})
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    applied_commission_amount = fields.Float()

    @api.model
    def create(self, vals):
        if self._context.get('purchase_price'):
            vals['purchase_price'] = self._context.get('purchase_price')
        return super().create(vals)


class PrestashopSaleOrder(models.Model):
    _inherit = "prestashop.sale.order"

    commission_amount = fields.Float()

    @api.multi
    def write(self, vals):
        can_edit = True
        if "prestashop_order_line_ids" in vals and vals["prestashop_order_line_ids"]:
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

    @job(default_channel="root.prestashop")
    @related_action(action="related_action_unwrap_binding")
    @api.multi
    def export_sale_state(self, new_state):
        for sale in self:
            if not new_state:
                continue
            with sale.backend_id.work_on(self._name) as work:
                exporter = work.component(usage="sale.order.state.exporter")
                return exporter.run(self, new_state)
