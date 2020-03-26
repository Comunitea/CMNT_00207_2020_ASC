# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tools.float_utils import float_is_zero
from odoo import api, models, fields


class StockMove(models.Model):
    _inherit = "stock.move"

    move_line_lot_ids = fields.Many2many(
        "stock.production.lot",
        string="Lots",
        compute="_compute_move_line_lot_ids",
    )
    proposed_lot_ids = fields.Many2many(
        "stock.production.lot",
        string="Lots",
        help="Lots/serial for moves when assign move",
    )

    @api.multi
    def _compute_move_line_lot_ids(self):
        for move in self:
            move.move_line_lot_ids = move.move_line_ids.mapped("lot_id")

    @api.multi
    def apply_proposed_lots(self):
        if not self:
            return
        move_ids = self.filtered(
            lambda x: x.picking_type_id.code == "incoming"
            and x.picking_type_id.use_proposed_lots
            and x.proposed_lot_ids
            and x.state in ["assigned", "confirmed", "partially_available"]
        )
        if not move_ids:
            return
        roundings = {move: move.product_id.uom_id.rounding for move in self}
        assigned_moves = self.env["stock.move"]
        partially_available_moves = self.env["stock.move"]
        confirmed_moves = self.env["stock.move"]

        for move in move_ids:
            if (
                move.location_id.should_bypass_reservation()
                and move.product_id.tracking == "serial"
                and move.picking_type_id.use_proposed_lots
            ):
                rounding = roundings[move]
                lots = self.env["stock.production.lot"].browse(
                    move.proposed_lot_ids.ids
                )
                for sml in move.move_line_ids.filtered(
                    lambda x: not x.lot_name and not x.lot_id
                ):
                    if lots:
                        sml.lot_name = lots[0].name
                        sml.qty_done = 1
                        lots -= lots[0]
                if lots:
                    for lot in lots:
                        move_line_vals_list = dict(
                            move._prepare_move_line_vals(quantity=1),
                            qty_done=1,
                            lot_name=lot.name,
                        )
                        self.env["stock.move.line"].create(move_line_vals_list)
                move.proposed_lot_ids.unlink()
                move.move_line_ids.filtered(lambda x: not x.lot_name).unlink()
                if float_is_zero(
                    move.quantity_done, precision_rounding=rounding
                ):
                    confirmed_moves |= move
                elif (
                    float_is_zero(
                        move.product_uom_qty - move.quantity_done,
                        precision_rounding=rounding,
                    )
                    or move.quantity_done > move.product_uom_qty
                ):
                    assigned_moves |= move
                else:
                    partially_available_moves |= move
        partially_available_moves.write({"state": "partially_available"})
        assigned_moves.write({"state": "assigned"})
        confirmed_moves.write({"state": "confirmed"})
        self.mapped("picking_id")._check_entire_pack()

    def _action_assign(self):
        # Tengo que hacer el action_Assign uno a uno para pasar en el
        # contexto los lotes permidos a la busqueda de quants
        move_ids = self.filtered(
            lambda x: x.picking_type_id.code != "incoming"
            and x.picking_type_id.use_proposed_lots
            and x.proposed_lot_ids
            and x.state in ["assigned", "confirmed", "partially_available"]
        )
        if move_ids:
            ctx = self._context.copy()
            for move in move_ids:
                ctx.update(proposed_lot_ids=move.proposed_lot_ids.ids)
                super(StockMove, move.with_context(ctx))._action_assign()
                move.move_line_ids.filtered(lambda x: x.lot_id).write(
                    {"qty_done": 1}
                )
                self -= move
        super()._action_assign()
        self.apply_proposed_lots()

    @api.multi
    def unload_lot_list(self):
        for move in self:
            self.proposed_lot_ids = False

    @api.multi
    def load_lot_list(self):
        # list_lot_ids = self.get_list_lot_ids()
        list_lot_ids = ["1001", "1002", "1003", "1004", "1005"]
        return self.apply_lot_list(list_lot_ids)

    @api.multi
    def apply_lot_list(self, list_lot_ids=[]):
        self.ensure_one()
        if not list_lot_ids:
            list_lot_ids = ["1001", "1002", "1003", "1004", "1005"]
        move_lot_names = self.move_line_lot_ids.mapped(
            "name"
        ) + self.move_line_ids.mapped("lot_name")
        list_lot_ids = [x for x in list_lot_ids if x not in move_lot_names]
        print(list_lot_ids)
        if list_lot_ids:
            lot_ids = self.env["stock.production.lot"]
            for name in list_lot_ids:
                lot_domain = [
                    ("product_id", "=", self.product_id.id),
                    ("name", "=", name),
                ]
                existing_lot = lot_ids.search(lot_domain, limit=1)
                if not existing_lot:
                    new_lot_vals = {
                        "product_id": self.product_id.id,
                        "name": name,
                    }
                    existing_lot = lot_ids.create(new_lot_vals)
                lot_ids |= existing_lot
            self.proposed_lot_ids |= lot_ids
        # self.check_move_line_ids()

    def check_move_line_ids(self):
        if (
            self.state in ("confirmed", "assigned")
            and self.picking_type_id.code == "incoming"
        ):
            self.move_line_ids.unlink()
            for lot in self.proposed_lot_ids:
                move_line = self.env["stock.move.line"].create(
                    dict(
                        self._prepare_move_line_vals(quantity=1),
                        qty_done=1,
                        lot_name=lot.name,
                    )
                )
                self.write({"move_line_ids": [(4, move_line.id)]})

    @api.multi
    def get_new_splot_ids(self):
        self.ensure_one()
        action = self.env.ref(
            "stock_move_lot_list.view_new_splot_wzd_act_window"
        ).read()[0]
        # prefiero crearllo y devolverlo que hacerlo con default get
        vals = {"product_id": self.product_id.id, "move_id": self.id}
        wzd_id = self.env["new.splot.wzd"].create(vals)
        action["domain"] = [("id", "=", wzd_id.id)]
        return action
