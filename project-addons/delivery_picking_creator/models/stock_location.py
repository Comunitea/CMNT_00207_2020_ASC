# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError

class StockLocation(models.Model):
    _inherit='stock.location'

    def should_bypass_reservation(self):
        if self._context.get('delivery_type', False):
            return False
        return super().should_bypass_reservation()