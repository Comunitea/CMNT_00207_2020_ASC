# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

from odoo import api, models, fields, _

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        quants = super()._gather(product_id=product_id, location_id=location_id, lot_id=lot_id, package_id=package_id,
                               owner_id=owner_id, strict=strict)

        if self._context.get('proposed_lot_ids', False):
            quants = quants.filtered(lambda x: x.lot_id.id in self._context['proposed_lot_ids'])
        return quants