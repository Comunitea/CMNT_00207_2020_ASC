# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tools.float_utils import float_compare, float_round, float_is_zero

from odoo import api, models, fields, _

class StockLocation(models.Model):
    _inherit = 'stock.location'

    deposit_location = fields.Boolean('Customer deposit', default = False)
    # bypass_owner = fields.Boolean('Bypass owner', default = False, help="Sometimes, we need to overwrite owner in stock location")
    #
    # @api.multi
    # def write(self, vals):
    #
    #     super().write(values=vals)
    #     if 'bypass_owner' in vals:
    #         for location in self:
    #             location.child_ids.write({'bypass_owner': vals['bypass_owner']})
    #
    #     return True

    def should_bypass_reservation(self):
        ## Las ubicaciones de depóstio nunca deberían de saltarse el bypass reservtion, aunque sea de proveedor o de cliente
        if self.deposit_location:
            return False
        return super().should_bypass_reservation()


