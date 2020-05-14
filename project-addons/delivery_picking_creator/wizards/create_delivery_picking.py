# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class DeliveryPickingWzdLine(models.TransientModel):
    _name = "delivery.picking.wzd.line"

    wzd_id = fields.Many2one("delivery.picking.wzd")
    selected = fields.Boolean('Selected')
    picking_id = fields.Many2one("stock.picking")
    n_lines = fields.Integer('# Lines')

class DeliveryPickingWzdLine(models.TransientModel):
    """Wzd to select outgoing picking to create new one for delivery
    """

    _name = "delivery.picking.wzd"
    _description = "Wzd to create delivery picking for same partner"

    picking_type_id = fields.Many2one("stock.move", "Move")
    partner_id = fields.Many2one('res.partner', string="Delivery adress")
    line_ids = fields.Many2many("delivery.picking.wzd.line", string= "Lines")

    carrier_id = fields.Many2one("delivery.carrier", string="Carrier")
    carrier_tracking_ref = fields.Char(string='Tracking Reference', copy=False)

    @api.model
    def default_get(self, field_list):
        res = super(DeliveryPickingWzdLine, self).default_get(field_list)
        if self._context.get('active_id', False) and self._context.get('create_delivery', False):
            pick = self.env['stock.picking'].browse(self._context['active_id'])
            picking_type_id = self.env.ref(
                'delivery_picking_creator.delivery_picking_type')
            partner_id = pick.partner_id
            picking_ids = self.get_same_partner_picks(partner_id.id)
            new_lines = self.env["delivery.picking.wzd.line"]
            for pick in picking_ids:
                val = {'picking_id': pick.id, 'n_lines': len(pick.move_lines)}
                new_lines |= self.line_ids.create(val)
            field_list = {'partner_id': partner_id.id,
                          'picking_type_id':picking_type_id.id,
                          'line_ids': [(6, 0, new_lines.ids)]}
            res.update(field_list)
        return res

    @api.multi
    def create_new_delivery_picking(self, picking_ids):
        partner_ids = picking_ids.mapped('partner_id')
        delivery_ids = self.env['stock.picking']
        for partner_id in partner_ids:
            ## creo un nuevo albarán
            vals = self.env['stock.picking']._update_delivery_picking_values(partner_id)
            partner_pick_ids = picking_ids.filtered(lambda x: x.partner_id == partner_id and x.state=='done')
            if not partner_pick_ids:
                continue
            origin = partner_pick_ids[0].origin
            for pick in partner_pick_ids[1:]:
                origin = '{} {}'.format(origin, pick.origin)
            vals['origin'] = origin
            picking_id = self.env['stock.picking'].create(vals)
            delivery_ids |= picking_id
            move_lines = partner_pick_ids.mapped('move_lines').filtered(lambda x: x.state == 'done')
            for move in move_lines:
                move.new_delivery_move(picking_id)
        action_picking = self.env.ref('stock.action_picking_tree_ready')
        action = action_picking.read()[0]
        action['context'] = {}
        action['domain'] = [('id', 'in', delivery_ids.ids)]
        return action

    def get_same_partner_picks(self, partner_id):
        domain = [('partner_id', '=', partner_id),
                  ('picking_type_id.code', '=', 'outgoing'),
                  ('state', '=', 'done'),
                  ('delivery_picking_id', '=', False)]
        picking_ids = self.env['stock.picking'].search(domain, order="date_done desc")
        return picking_ids

    @api.multi
    def action_find_picking(self):
        picking_ids = self.get_same_partner_picks(self.partner_id.id)
        for pick in picking_ids:
            val = {'picking_id': pick.id, 'n_lines': len(pick.move_line), 'wzd_id': self.id}
            new_line = self.line_ids.create(val)

    @api.multi
    def action_create_picking(self):
        return self.create_new_delivery_picking(self.line_ids.filtered(lambda x: x.selected).mapped('picking_id'))



