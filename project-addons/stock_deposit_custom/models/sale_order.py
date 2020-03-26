# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    deposit = fields.Boolean("Deposit")
    deposit_date = fields.Date("Date Dep.")
    qty_in_deposit = fields.Float(
        string="Quantity in deposit",
        compute="_compute_qty_in_deposit",
        store=True,
        digits=dp.get_precision("Product Unit of Measure"),
        required=True,
        default=0.0,
    )
    advise_deposit_mail = fields.Boolean("Advise deposit mail", default=False)
    deposit_move_ids = fields.One2many(
        "stock.move", "deposit_line_id", string="Stock Moves"
    )

    @api.onchange("route_id")
    def _onchange_route_id_set_deposit(self):
        self.deposit = (
            self.route_id
            and self.route_id.rule_ids
            and self.route_id.rule_ids[0].location_id.deposit_location
        )

    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(
            group_id
        )
        if self.deposit:
            values.update(deposit_line_id=self.id)
        return values

    @api.multi
    @api.depends(
        "deposit_move_ids.state",
        "deposit_move_ids.scrapped",
        "deposit_move_ids.product_uom_qty",
        "deposit_move_ids.product_uom",
    )
    def _compute_qty_in_deposit(self):
        for line in self.filtered("deposit"):
            qty = 0.00
            move_to_check = line.deposit_move_ids.filtered(
                lambda x: x.state == "done"
            )
            if move_to_check:
                for move in move_to_check:
                    if move.location_dest_id.deposit_location:
                        qty += move.product_uom._compute_quantity(
                            move.product_uom_qty, line.product_uom
                        )
                    elif move.location_id.deposit_location:
                        qty -= move.product_uom._compute_quantity(
                            move.product_uom_qty, line.product_uom
                        )
                line.qty_in_deposit = qty


class SaleOrder(models.Model):
    _inherit = "sale.order"

    deposit_count = fields.Integer(
        string="# of Deposits", compute="_compute_deposit_count"
    )
    deposit_ids = fields.One2many(
        "sale.order.line", compute="_compute_deposit_ids"
    )
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
            sale.deposit_date = min(x.deposit_date for x in sale.deposit_ids)

    @api.multi
    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            deposit_ids = order.order_line.filtered("deposit")
            for line in deposit_ids:
                current_date = line.order_id.date_order
                delta = timedelta(days=line.order_id.partner_id.deposit_days)
                result = current_date + delta
                line.deposit_date = result.strftime(DEFAULT_SERVER_DATE_FORMAT)
            order.deposit_date = min(line.deposit_date for line in deposit_ids)
        return res

    @api.multi
    def action_open_deposit(self):
        self.ensure_one()
        action = self.env.ref(
            "stock_deposit_custom.act_sale_order_2_deposit"
        ).read()[0]
        action["domain"] = self.compute_deposit_domain()
        return action

    @api.model
    def send_advise_email(self):
        # Busco ventas con líneas de depósitos
        deposit_ids = self.env["sale.order"]
        so_ids = (
            self.env["sale.order.line"]
            .search(
                [
                    ("deposit", "=", True),
                    #  ('advise_deposit_mail', '=', False),
                    ("qty_in_deposit", ">", 0),
                    ("deposit_date", "=", fields.Date.today()),
                ]
            )
            .mapped("order_id")
        )
        # Busco el albarán asociado a la venta/depósito
        for so in so_ids:
            pickings = so.mapped("picking_ids").filtered(
                lambda x: x.state in ("done", "sale")
                and x.picking_type_id.is_deposit
            )
            if pickings:
                deposit_ids |= so

        # ~ mail_pool = self.env['mail.mail']
        # ~ mail_ids = self.env['mail.mail']
        template = self.env.ref(
            "stock_deposit_custom.stock_deposit_advise_partner", False
        )
        for deposit in deposit_ids:
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
            composer_id = (
                self.env["mail.compose.message"].with_context(ctx).create({})
            )
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
