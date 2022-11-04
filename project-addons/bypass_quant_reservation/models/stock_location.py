# -*- coding: utf-8 -*-
# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _

class StockLocation(models.Model):
    _inherit = "stock.location"

    should_bypass_quant_reservation = fields.Boolean("Bypass Quant Reservation", default=False)

    # def should_bypass_reservation(self):
    #     if self.should_bypass_quant_reservation:
    #         return True
    #     return super().should_bypass_reservation()

    @api.multi
    def write(self, vals):
        res = super().write(vals)
        if 'should_bypass_quant_reservation' in vals:
            for location in self:
                location.child_ids.write({'should_bypass_quant_reservation': vals['should_bypass_quant_reservation']})
        return res

