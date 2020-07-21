# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    deposit = fields.Boolean("Deposit")
    deposit_date = fields.Date("Date Dep.")
    qty_in_deposit = fields.Float(
        string="Quantity in deposit",
        digits=dp.get_precision("Product Unit of Measure"),
        required=True,
        default=0.0,
        copy=False,
    )
    advise_deposit_mail = fields.Boolean(
        "Advise deposit mail", default=False, copy=False
    )
    deposit_move_ids = fields.One2many(
        "stock.move", "deposit_line_id", string="Deposit Stock Moves"
    )

    @api.onchange("route_id")
    def _onchange_route_id_set_deposit(self):
        deposit_route = any(
            x.location_src_id.usage == "internal" and x.location_id.deposit_location
            for x in self.route_id.rule_ids
        )
        self.deposit = self.route_id and deposit_route

    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        if self.deposit:
            values.update(deposit_line_id=self.id)
        return values

    def compute_str_lots(self):
        str = ""
        if self.product_id.tracking != "none":
            lot_ids = self.get_line_quants().mapped("lot_id")
            if lot_ids:
                str = "Serie: {}".format(lot_ids[0].name)
                for lot in lot_ids[1:]:
                    str = format("{}, {}".format(str, lot.name))
        return str

    def get_line_quants(self):
        Quants = self.env["stock.quant"]
        domain = [("move_id.deposit_line_id", "=", self.id), ("state", "=", "done")]
        lot_ids = self.env["stock.move.line"].search_read(domain, ["lot_id"])
        if lot_ids:
            q_domain = [
                ("lot_id", "in", [x["lot_id"][0] for x in lot_ids]),
                ("location_id.deposit_location", "=", True),
            ]
            Quants = Quants.search(q_domain)
        return Quants

    def _compute_qty_in_deposit(self):
        # Al filtrar por tipo de albarán is_deposit puedo mover mercancia
        # a/desde deposito sin que influya en la cantidad en deposito a
        # la hora tenerla en cuenta
        for line in self.filtered("deposit"):
            qty = 0.00
            move_to_check = line.deposit_move_ids.filtered(
                lambda x: x.state == "done" and x.picking_type_id.is_deposit
            )
            if move_to_check:
                for move in move_to_check:
                    if move.location_dest_id.deposit_location:
                        qty += move.product_uom._compute_quantity(
                            move.quantity_done, line.product_uom
                        )
                    elif move.location_id.deposit_location:
                        qty -= move.product_uom._compute_quantity(
                            move.quantity_done, line.product_uom
                        )
                print(qty)
                line.qty_in_deposit = qty

    def action_show_deposit_lots(self):
        if self.product_id.tracking != "none":
            quant_ids = self.get_line_quants()
            if quant_ids:
                action = self.env.ref("stock.location_open_quants").read()[0]
                action["domain"] = [("id", "in", quant_ids.ids)]
                action["context"] = dict(self.env.context)
                return action


class SaleOrder(models.Model):
    _inherit = "sale.order"

    deposit_count = fields.Integer(
        string="# of Deposits", compute="_compute_deposit_count"
    )
    deposit_ids = fields.One2many("sale.order.line", compute="_compute_deposit_ids")
    deposit_date = fields.Date("Date Dep.")

    def compute_deposit_domain(self):
        return [("order_id", "=", self.id), ("deposit", "=", True)]

    @api.multi
    def _compute_deposit_count(self):
        sol = self.env["sale.order.line"]
        for sale in self.filtered(lambda x: x.state in ("sale", "done")):
            domain = sale.compute_deposit_domain()
            sale.deposit_count = sol.search_count(domain)

    @api.multi
    def _compute_deposit_ids(self):
        sol = self.env["sale.order.line"]
        for sale in self.filtered(lambda x: x.state in ("sale", "done")):
            domain = sale.compute_deposit_domain()
            sale.deposit_ids = sol.search(domain)
            if sale.deposit_ids:
                sale.deposit_date = min(x.deposit_date for x in sale.deposit_ids)

    @api.multi
    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            deposit_ids = order.order_line.filtered("deposit")
            if not deposit_ids:
                continue
            for line in deposit_ids:
                current_date = line.order_id.date_order
                delta = timedelta(days=line.order_id.partner_id.deposit_days)
                result = current_date + delta
                line.deposit_date = result.strftime(DEFAULT_SERVER_DATE_FORMAT)
            if deposit_ids:
                order.deposit_date = min(line.deposit_date for line in deposit_ids)
        return res

    @api.multi
    def action_open_deposit(self):
        self.ensure_one()
        action = self.env.ref("stock_deposit_custom.act_sale_order_2_deposit").read()[0]
        action["domain"] = self.compute_deposit_domain()
        return action

    def compute_send_advise_domain(self):
        to_date = self._context.get(
            "to_date", fields.Date.from_string(fields.Date.today())
        )
        domain = [("deposit", "=", True), ("deposit_date", "=", to_date)]
        return domain

    @api.model
    def send_advise_email(self):
        # Busco ventas con líneas de depósitos
        deposit_ids = self.env["sale.order"]

        order_lines = (
            self.env["sale.order.line"]
            .search(self.compute_send_advise_domain())
            .filtered(lambda x: x.qty_in_deposit > 0)
        )
        so_ids = order_lines.mapped("order_id")
        if not so_ids:
            return
        # Busco el albarán asociado a la venta/depósito
        # Si quiero mover stock a/desde depñósito sin que tenga influencia
        # en el stock del depósito, tengo que utilizar un tipo de albarán
        # marcado como no depósito
        for so in so_ids:
            pickings = so.mapped("picking_ids").filtered(
                lambda x: x.state in ("done", "sale") and x.picking_type_id.is_deposit
            )
            if pickings:
                deposit_ids |= so
        # ~ mail_pool = self.env['mail.mail']
        # ~ mail_ids = self.env['mail.mail']
        template = self.env.ref(
            "stock_deposit_custom.stock_deposit_advise_partner", False
        )
        for deposit in so_ids:
            ctx = dict(self._context)
            ctx.update(
                {
                    "default_model": "sale.order",
                    "default_res_id": deposit.id,
                    "default_use_template": bool(template.id),
                    "default_template_id": template.id,
                    "default_composition_mode": "comment",
                    "mark_so_as_sent": True,
                }
            )
            composer_id = self.env["mail.compose.message"].with_context(ctx).create({})
            values = composer_id.onchange_template_id(
                template.id, "comment", deposit.name, deposit.id
            )["value"]
            composer_id.write(values)
            composer_id.with_context(ctx).send_mail()
            deposit.advise_deposit_mail = True
            # ~ mail_id = template.send_mail(deposit.id)
            # ~ mail_ids += mail_pool.browse(mail_id)
        # ~ if mail_ids:
        # ~ mail_ids.send()
        return True
