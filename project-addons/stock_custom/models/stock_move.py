# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = "stock.move"

    def _search_picking_for_assignation(self):
        self.ensure_one()
        picking = self.env['stock.picking'].search([
            ('group_id', '=', self.group_id.id),
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_dest_id.id),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('printed', '=', False),
            ('scheduled_date', '=', self.date_expected),
            ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
        return picking

    def reassing_split_from_picking(self):
        picking_id = self.mapped('picking_id')
        if picking_id.state in ['cancel', 'draft', 'done']:
            raise UserError('El albarań %s está en estado incorrecto: %s'%(picking_id.name, picking_id.state))
        if len(picking_id) != 1:
            raise UserError('Todos los movimientos deben ser del mismo albarán')
        if any(x.picking_id == False for x in self):
            raise UserError('Todos los movimientos deben tener ya un albarán asignado')
        scheduled_date = picking_id.scheduled_date
        moves_to_split = self.filtered(lambda x: x.date_expected != scheduled_date)
        moves_to_split.write({'picking_id': False})
        backorder_ids = self.env['stock.picking']
        dates = {}
        for move in moves_to_split:
            if not move.date_expected in dates.keys():
                dates[move.date_expected] = move.date_expected

        if dates:
            for date in dates.keys():
                dates[date] = moves_to_split.filtered(lambda x: x.date_expected == date)
                if picking_id.scheduled_date == date:
                    dates[date].write({'picking_id': picking_id})
                else:
                    backorder_picking = picking_id.copy({
                        'name': '/',
                        'move_lines': [],
                        'move_line_ids': [],
                        'backorder_id': picking_id.id,
                    })
                    picking_id.message_post(
                        body=_(
                            'Este albarán ha creado un nuevo albarán <a href="#" '
                            'data-oe-model="stock.picking" '
                            'data-oe-id="%d">%s</a> al cambiar la fecha de estimada a %s.'
                        ) % (
                                 backorder_picking.id,
                                 backorder_picking.name,
                                 date
                             )
                    )
                    dates[date].write({
                        'picking_id': backorder_picking.id,
                    })
                    dates[date].mapped('move_line_ids').write({
                        'picking_id': backorder_picking.id,
                    })
                    backorder_ids |= backorder_picking
                    print("se ha creado el %s" % backorder_picking.name)
        return backorder_ids
        """
            if backorder_ids:
                action = self.env.ref('stock.action_picking_tree_all').read()[0]
                action['domain'] = [('id', 'in', backorder_ids.ids)]
                return action
            """       
