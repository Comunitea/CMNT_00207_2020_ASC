# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class StockLocation(models.Model):
    _inherit = "stock.location"

    def should_bypass_reservation(self):
        if self._context.get("delivery_type", False):
            return False
        return super().should_bypass_reservation()
