# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from datetime import datetime, timedelta

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def write(self, vals):
        if 'state' in vals and vals['state'] == 'purchase':
            ## añado como seguidor a quien confirme el pedido de compra
            for purchase in self:
                partner_id = purchase.env.user and purchase.env.user.partner_id or False
                if partner_id and partner_id not in self.message_follower_ids.mapped('partner_id'):
                    self.message_subscribe(partner_ids=partner_id.ids)
        return super().write(vals)

