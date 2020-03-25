# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_deposit = fields.Boolean('Is deposit', default=False)

class StockMove(models.Model):
    _inherit = 'stock.move'

    deposit_line_id = fields.Many2one('sale.order.line')

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
