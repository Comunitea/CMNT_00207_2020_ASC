# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
from odoo.addons import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"
    
    @api.multi
    def _compute_qty_available_at_expected_date(self):
        ctx = self._context.copy()
        for move in self:
            to_date = move.date+relativedelta(minutes=30)
            ctx.update(to_date=to_date)
            product = move.product_id.with_context(ctx)
            move.virtual_available = product.virtual_available
    
    virtual_available = fields.Float(
        'Forecasted Quantity', compute='_compute_qty_available_at_expected_date',
        digits=dp.get_precision('Product Unit of Measure'))
