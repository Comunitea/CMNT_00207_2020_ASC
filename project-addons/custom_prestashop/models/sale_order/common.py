# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields, _
from odoo.addons.queue_job.job import job, related_action
from datetime import timedelta
from odoo.addons.component.core import Component
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):

    _inherit = "sale.order"

    delivered = fields.Boolean()
    manual_ready_to_send = fields.Boolean()

    @api.onchange("payment_mode_id")
    def onchange_payment_mode_id(self):
        if self.payment_mode_id and self.payment_mode_id.defaullt_sale_invoice_policy:
            self.invoice_policy = self.payment_mode_id.defaullt_sale_invoice_policy

    def _create_delivery_line(self, carrier, price_unit):
        return super(
            SaleOrder, self.with_context(purchase_price=price_unit)
        )._create_delivery_line(carrier, price_unit)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.prestashop_state.trigger_paid:
            res.ready_to_send = True
        return res

    @api.multi
    def action_confirm(self):
        return super(SaleOrder, self.with_context(bypass_risk=True)).action_confirm()

    @api.multi
    def action_unlock(self):
        return super(SaleOrder, self.with_context(bypass_risk=True, bypass_risk_exception=True)).action_unlock()

    def check_risk_exception(self):
        if not self.payment_mode_id.check_risk:
            return False
        if self.state == "cancel" or self._context.get('bypass_risk_exception'):
            return False
        partner = self.partner_id.commercial_partner_id
        exception_msg = ""
        if partner.risk_exception:
            exception_msg = _("Financial risk exceeded.\n")
        elif partner.risk_sale_order_limit and not partner.risk_sale_order_limit == 0.0 and (
            (partner.risk_sale_order + self.amount_total)
            > partner.risk_sale_order_limit
        ):
            exception_msg = _("This sale order exceeds the sales orders risk.\n")
        elif partner.risk_sale_order_include and not partner.credit_limit == 0.0 and (
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
                if state.trigger_paid and not order.manual_ready_to_send:
                    order.ready_to_send = True
                    order.picking_ids.write({"ready_to_send": True})
            if 'ready_to_send' in vals and self._context.get('manual_ready_to_send'):
                order.picking_ids.write({"ready_to_send": vals["ready_to_send"]})
                if not vals['ready_to_send']:
                    batch_pickings = order.mapped('picking_ids.batch_id')
                    for batch in batch_pickings:
                        if batch.user_id:
                            raise UserError('El albarán {} ya se está procesando, no se puede desmarcar'.format(batch.name))
                order.write({"manual_ready_to_send": True})
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    applied_commission_amount = fields.Float()

    @api.model
    def create(self, vals):
        if self._context.get("purchase_price"):
            vals["purchase_price"] = self._context.get("purchase_price")
        return super().create(vals)


class PrestashopSaleOrder(models.Model):
    _inherit = "prestashop.sale.order"

    commission_amount = fields.Float()

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.with_delay(eta=30).export_order()
        return res

    @api.multi
    def write(self, vals):
        can_edit = True
        if "prestashop_order_line_ids" in vals and vals["prestashop_order_line_ids"]:
            for picking in self.odoo_id.picking_ids:
                if picking.state in ("assigned", "done"):
                    can_edit = False
            if not can_edit:
                vals.pop("prestashop_order_line_ids")
                return super().write(vals)
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

    @job(default_channel="root.prestashop")
    def import_orders_since(self, backend, since_date=None, **kwargs):
        """ Prepare the import of orders modified on PrestaShop """
        filters = None
        if since_date:
            filters = {"date": "1", "filter[date_upd]": ">[%s]" % (since_date)}
        if backend.start_import_date:
            if not since_date:
                filters = {"date": "1"}
            filters["filter[date_add]"] = ">[{}]".format(backend.start_import_date)
        now_fmt = fields.Datetime.now()
        self.env["prestashop.sale.order"].import_batch(
            backend, filters=filters, priority=5, max_retries=0
        )

        # substract a 10 second margin to avoid to miss an order if it is
        # created in prestashop at the exact same time odoo is checking.
        next_check_datetime = now_fmt - timedelta(seconds=10)
        backend.import_orders_since = next_check_datetime
        return True

    @job(default_channel='root.prestashop')
    def export_order(self):
        self.ensure_one()
        with self.backend_id.work_on('prestashop.sale.order.log') as work:
            exporter = work.component(usage="order_log.exporter")
            return exporter.run(self)


class PrestashopSaleOrderLine(models.Model):
    _inherit = "prestashop.sale.order.line"

    @api.multi
    def unlink(self):
        if self.odoo_id:
            self.odoo_id.unlink()
        return super().unlink()


class SaleOrderOnChange(Component):

    _inherit = "ecommerce.onchange.manager.sale.order"

    order_onchange_fields = [
        "partner_id",
        "partner_shipping_id",
        "payment_mode_id",
        "workflow_process_id",
        "carrier_id",
    ]


class OrderLog(Component):
    _name = 'prestashop.order.log.adapter'
    _inherit = 'prestashop.adapter'
    _apply_on = '__not_exit_prestashop.orderodoo'

    _prestashop_model = 'orderodoo'
    _export_node_name = 'orderodoo'


class OrderLogModel(models.TransientModel):
    # In actual connector version is mandatory use a model
    _name = '__not_exit_prestashop.orderodoo'
    _description = 'Dummy Transient model for Order Log'
