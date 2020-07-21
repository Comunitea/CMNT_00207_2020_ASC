# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    pickup_signature = fields.Binary()

    @api.onchange("carrier_id")
    def _onchange_carrier_id(self):
        if self.carrier_id:
            self.carrier_service = self.carrier_id.service_code
