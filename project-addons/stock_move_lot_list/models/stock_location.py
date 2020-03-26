# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class StockLocation(models.Model):
    _inherit = "stock.location"

    deposit_location = fields.Boolean("Customer deposit", default=False)

    def should_bypass_reservation(self):
        res = super().should_bypass_reservation()
        if self.deposit_location:
            return False
        return res
