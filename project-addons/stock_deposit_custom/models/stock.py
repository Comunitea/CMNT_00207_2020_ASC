# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    def _prepare_move_values(self):
        vals = super()._prepare_move_values()
        if self.picking_id.picking_type_id.is_deposit:
            move_id = self.picking_id.move_lines.filtered(lambda x: x.product_id == self.product_id)[0]
            vals.update(deposit_line_id=move_id.deposit_line_id.id)
        return vals

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_deposit = fields.Boolean('Is deposit', default=False)

# class StockQuant (models.Model):
#     _inherit="stock.quant"
#
#     def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
#         if location_id.bypass_owner and owner_id:
#             owner_id = False
#         return super()._gather(product_id=product_id, location_id=location_id, lot_id=lot_id, package_id=package_id,
#                                owner_id=owner_id, strict=strict)

class StockMove(models.Model):
    _inherit = 'stock.move'

    deposit_line_id = fields.Many2one('sale.order.line')
    #
    # @api.multi
    # def _action_done(self):
    #     for move in self.filtered('picking_type_id.is_deposit'):
    #         if move.location_dest_id.deposit_location:
    #             move.move_line_ids.write({'owner_id': move.partner_id.id})
    #         else:
    #             move.move_line_ids.write({'owner_id': False})
    #     return super(StockMove, self)._action_done()


    def _prepare_procurement_values(self):
        vals = super()._prepare_procurement_values()
        vals.update(deposit_line_id=self.deposit_line_id.id)
        return vals

# class StockRule(models.Model):
#     _inherit = 'stock.rule'
#
#     def _get_stock_move_values(self, product_id, product_qty, product_uom,
#                                location_id, name, origin, values, group_id):
#         vals = super()._get_stock_move_values(
#             product_id, product_qty, product_uom,
#             location_id, name, origin, values, group_id)
#         return vals
