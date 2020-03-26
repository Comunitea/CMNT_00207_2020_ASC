# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tools.float_utils import float_compare, float_round, float_is_zero

from odoo import api, models, fields, _


class StockLocation(models.Model):
    _inherit = "stock.location"

    deposit_location = fields.Boolean("Customer deposit", default=False)

    def should_bypass_reservation(self):
        res = super().should_bypass_reservation()
        if self.deposit_location:
            return False
        return res
