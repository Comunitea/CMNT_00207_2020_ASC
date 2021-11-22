# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, _
from odoo.exceptions import ValidationError


class RmaMakePicking(models.TransientModel):
    _inherit = 'rma_make_picking.wizard'

    # def action_create_picking(self):
    #     res = super().action_create_picking()
    #     if res.get('res_id'):
    #         picking_ids = res['res_id']
    #     else:
    #         picking_ids = res['domain'][0][2]
    #     pickings = self.env['stock.picking'].browse(picking_ids)
    #     pickings.filtered(lambda r: not r.partner_id).write({'partner_id': self.item_ids.line_id.partner_id.id})
    #     for picking in pickings.filtered(lambda r: r.state not in ('done', 'cancel')):
    #         if picking.picking_type_code == 'incoming':
    #             if picking.state == 'confirmed':
    #                 picking.action_assign()
    #             lot_id = self.item_ids.line_id.lot_id.id
    #             picking.move_line_ids.write({
    #                 'qty_done': 1,
    #                 'lot_id': lot_id
    #             })
    #         if picking.picking_type_code == 'outgoing' and self.item_ids.line_id.repair_ids:
    #                 if picking.state == 'confirmed':
    #                     picking.action_assign()
    #                 lot_id = self.item_ids.line_id.lot_id.id
    #                 picking.move_line_ids.write({
    #                     'lot_id': lot_id
    #                 })

    #     return res

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

    @api.model
    def _get_procurement_data(self, item, group, qty, picking_type):
        line = item.line_id
        res = super()._get_procurement_data(item, group, qty, picking_type)
        res['origin'] = line.rma_id and line.rma_id.name or line.name
        res['partner_id'] = line.rma_id.delivery_address_id.id or line.rma_id.partner_id.id
        return res

    def _get_procurement_group_data(self, item):
        group_data = super()._get_procurement_group_data(item)
        group_data['partner_id'] = item.rma_id.delivery_address_id.id or item.rma_id.partner_id.id,
        return group_data

    @api.multi
    def _create_picking(self):
        """Method called when the user clicks on create picking"""
        picking_type = self.env.context.get('picking_type')
        procurements = []
        for item in self.item_ids:
            line = item.line_id
            if line.state != 'approved':
                raise ValidationError(
                    _('RMA %s is not approved') %
                    line.name)
            if line.receipt_policy == 'no' and picking_type == \
                    'incoming':
                raise ValidationError(
                    _('No shipments needed for this operation'))
            if line.delivery_policy == 'no' and picking_type == \
                    'outgoing':
                raise ValidationError(
                    _('No deliveries needed for this operation'))
            procurements.append(self._create_procurement(item, picking_type))
        return procurements

    @api.multi
    def action_create_picking(self):
        procurements = self._create_picking()
        action = self.env.ref('stock.do_view_pickings')
        action = action.read()[0]
        if procurements:
            pickings = self.env['stock.picking'].search(
                [('origin', 'in', procurements)]).ids
            if len(pickings) > 1:
                action['domain'] = [('id', 'in', pickings)]
            else:
                form = self.env.ref('stock.view_picking_form', False)
                action['views'] = [(form and form.id or False, 'form')]
                action['res_id'] = pickings and pickings[0]
        return action
