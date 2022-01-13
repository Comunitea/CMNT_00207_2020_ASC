# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = "stock.move"

    def _search_picking_for_assignation(self):
        self.ensure_one()
        domain = [
            ('group_id', '=', self.group_id.id),
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_dest_id.id),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('printed', '=', False),
            ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])]
        if not self.rma_line_id:
            domain.append(('scheduled_date', '=', self.date_expected))
        picking = self.env['stock.picking'].search(domain, limit=1)
        return picking

    def reassing_split_from_picking(self):
        picking_id = self.mapped('picking_id')
        if picking_id.state in ['cancel', 'draft', 'done']:
            raise UserError('El albarán %s está en estado incorrecto: %s'%(picking_id.name, picking_id.state))
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
                                 fields.Datetime.to_datetime(date).strftime('%d-%m-%y')
                             )
                    )
                    dates[date].write({
                        'picking_id': backorder_picking.id,
                    })
                    dates[date].mapped('move_line_ids').write({
                        'picking_id': backorder_picking.id,
                    })
                    backorder_ids |= backorder_picking
                    ## print("se ha creado el %s" % backorder_picking.name)
        return backorder_ids
        """
            if backorder_ids:
                action = self.env.ref('stock.action_picking_tree_all').read()[0]
                action['domain'] = [('id', 'in', backorder_ids.ids)]
                return action
            """

    @api.multi
    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            line = self.purchase_line_id
            order = line.order_id
            price_unit = line.price_unit
            price_unit = line._get_discounted_price_unit()
            if line.taxes_id:
                price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id, quantity=1.0)['total_excluded']
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                # The date must be today, and not the date of the move since the move move is still
                # in assigned state. However, the move date is the scheduled date until move is
                # done, then date of actual move processing. See:
                # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
                price_unit = order.currency_id._convert(
                    price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self), round=False)
            return price_unit
        return not self.company_id.currency_id.is_zero(self.price_unit) and self.price_unit or self.product_id.standard_price
