# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class PickingSignWizard(models.TransientModel):

    _name = 'picking.sign.wizard'

    signature = fields.Binary()

    def confirm(self):
        for batch_picking in self.env['stock.picking.batch'].browse(self.env.context.get('active_ids')):
            for picking in batch_picking.picking_ids:
                picking.write({
                    'pickup_signature': self.signature,
                    'delivered': True
                })
