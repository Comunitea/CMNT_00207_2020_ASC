# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, _
from odoo.exceptions import UserError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def unlink(self):

        picking_type_id = self.env.ref(
            'delivery_picking_creator.delivery_picking_type')
        if self.mapped('move_id').mapped('picking_type_id') == picking_type_id:
            ctx = self._context.copy()
            ctx.update(delivery_type=True)
            self = self.with_context(ctx)
        return super(StockMoveLine, self).unlink()


class StockMove(models.Model):
    _inherit = "stock.move"

    def _do_unreserve(self):
        picking_type_id = self.env.ref("delivery_picking_creator.delivery_picking_type")
        if self.mapped("picking_type_id") == picking_type_id:
            ctx = self._context.copy()
            ctx.update(delivery_type=True)
            self = self.with_context(ctx)
        return super(StockMove, self)._do_unreserve()

    def _action_assign(self):
        picking_type_id = self.env.ref("delivery_picking_creator.delivery_picking_type")
        if self.mapped("picking_type_id") == picking_type_id:
            ctx = self._context.copy()
            ctx.update(delivery_type=True)
            self = self.with_context(ctx)
        return super(StockMove, self)._action_assign()

    def update_delivery_move_values(self, picking_id):
        res = {
            "restrict_partner_id": self.partner_id.id,
            "move_dest_ids": False,
            "origin_returned_move_id": False,
            "move_orig_ids": [(6, 0, [self.id])],
            "group_id": False,
            "procure_method": "make_to_order",
            "location_id": picking_id.location_id.id,
            "picking_id": picking_id.id,
            "location_dest_id": picking_id.location_dest_id.id,
            "picking_type_id": picking_id.picking_type_id.id,
        }

        return res

    def new_delivery_move(self, picking_id):

        self = (
            self.with_prefetch()
        )  # This makes the ORM only look for one record and not 300 at a time, which improves performance
        if self.state != "done":
            raise UserError(
                _("You cannot split a stock move that has not been set to 'Done'.")
            )
        defaults = self.update_delivery_move_values(picking_id)
        defaults["picking_id"] = picking_id.id
        defaults["location_id"] = picking_id.location_id.id
        defaults["location_dest_id"] = picking_id.location_dest_id.id
        new_move = self.with_context(rounding_method="HALF-UP").copy(defaults)
        self.move_dest_ids = new_move
        return new_move
