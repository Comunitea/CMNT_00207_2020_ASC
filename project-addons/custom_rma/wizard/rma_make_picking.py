# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class RmaMakePicking(models.TransientModel):
    _inherit = 'rma_make_picking.wizard'

    def action_create_picking(self):
        res = super().action_create_picking()
        if res.get('res_id'):
            picking_ids = res['res_id']
        else:
            picking_ids = res['domain'][0][2]
        pickings = self.env['stock.picking'].browse(picking_ids)
        pickings.filtered(lambda r: not r.partner_id).write({'partner_id': self.item_ids.line_id.partner_id.id})
        for picking in pickings.filtered(lambda r: r.state not in ('done', 'cancel')):
            if picking.picking_type_code == 'incoming':
                if picking.state == 'confirmed':
                    picking.action_assign()
                lot_id = self.item_ids.line_id.lot_id.id
                picking.move_line_ids.write({
                    'qty_done': 1,
                    'lot_id': lot_id
                })
            if picking.picking_type_code == 'outgoing' and self.item_ids.line_id.repair_ids:
                    if picking.state == 'confirmed':
                        picking.action_assign()
                    lot_id = self.item_ids.line_id.lot_id.id
                    picking.move_line_ids.write({
                        'lot_id': lot_id
                    })

        return res

    def _prepare_item(self, line):
        values = {'product_id': line.product_id.id,
                  'product_qty': line.product_qty,
                  'uom_id': line.uom_id.id,
                  'qty_to_receive': line.qty_to_receive,
                  'qty_to_deliver': line.qty_to_deliver,
                  'line_id': line.id,
                  'rma_id': line.rma_id and line.rma_id.id or False,
                  }
        return values
