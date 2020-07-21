# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    def _prepare_move_values(self):
        vals = super()._prepare_move_values()
        if self.picking_id.picking_type_id.is_deposit:
            move_id = self.picking_id.move_lines.filtered(
                lambda x: x.product_id == self.product_id
            )[0]
            vals.update(deposit_line_id=move_id.deposit_line_id.id)
        return vals


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    is_deposit = fields.Boolean("Is deposit", default=False)


class StockMove(models.Model):
    _inherit = "stock.move"

    deposit_line_id = fields.Many2one("sale.order.line")

    @api.multi
    def _action_done(self):
        res = super(StockMove, self)._action_done()
        self.mapped("deposit_line_id")._compute_qty_in_deposit()
        return res

    def _prepare_procurement_values(self):
        vals = super()._prepare_procurement_values()
        vals.update(deposit_line_id=self.deposit_line_id.id)
        return vals
