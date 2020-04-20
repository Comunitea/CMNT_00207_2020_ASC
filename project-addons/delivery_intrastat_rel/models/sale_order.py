# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class SaleOrder(models.Model):

    _inherit = "sale.order"

    @api.onchange('carrier_id')
    def onchange_carrier_id(self):
        super().onchange_carrier_id
        if self.carrier_id:
            self.intrastat_transport_id = \
                self.carrier_id.intrastat_transport_id.id
