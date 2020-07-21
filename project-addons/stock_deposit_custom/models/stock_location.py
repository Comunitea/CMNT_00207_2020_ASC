# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields


class StockLocation(models.Model):
    _inherit = "stock.location"

    deposit_location = fields.Boolean("Customer deposit", default=False)

    def should_bypass_reservation(self):
        # Las ubicaciones de depóstio nunca deberían de saltarse el
        # bypass reservtion, aunque sea de proveedor o de cliente
        if self.deposit_location:
            return False
        return super().should_bypass_reservation()
