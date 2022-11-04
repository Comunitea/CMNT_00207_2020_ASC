# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockPickingToPDALines(models.TransientModel):
    _name = 'stock.picking.to.pda.lines'
    _description = 'Batch Picking Lines Picks'

    def _compute_box_domain(self):
        return [('is_box', '=', True)]

    wzd_id = fields.Many2one('stock.picking.to.pda', 'Wizard')
    picking_id = fields.Many2one('stock.picking', 'Picking')
    box_id = fields.Many2one('stock.location', 'Location', domain=_compute_box_domain)
    sale_id = fields.Many2one('sale.order')

    def compute_parent_move_line_ids(self):
        picking = self.picking_id
        wzd_id = self.wzd_id
        wzd_id.move_line_ids = picking.move_line_ids



class StockPickingToPDA(models.TransientModel):
    _name = 'stock.picking.to.pda'
    _description = 'Batch Picking Lines'

    batch_id = fields.Many2one('stock.picking.batch', string='PDA Batch', oldname="wave_id", domain="[('state', 'in', ['draft', 'assigned'])]")
    line_ids = fields.One2many('stock.picking.to.pda.lines', 'wzd_id', string="Picking")
    move_line_ids = fields.Many2many('stock.move.line', string="Moves")
    picking_type_id = fields.Many2one('stock.picking.type', string='Type', required=True)

    @api.model
    def default_get(self, fields):
        res = super(StockPickingToPDA, self).default_get(fields)

        if not fields:
            return res
        context = self.env.context

        picking_ids= self.env['stock.picking']
        if context.get('active_model') == 'stock.picking':
            active_ids = context.get('active_ids', False)
            picking_ids = self.env['stock.picking'].browse(active_ids)


        batch_domain = [('state', '=', 'draft')]
        batch_id = self.env['stock.picking.batch'].search(batch_domain, limit=1)

        if batch_id:
            picking_ids |= batch_id.picking_ids

        if not picking_ids:
            raise (_('No pickings to send'))
        picking_type_id = picking_ids[0].picking_type_id
        if all(x.batch_id == picking_ids[0].batch_id for x in picking_ids):
            batch_id = picking_ids[0].batch_id
        if not batch_id and False:
            batch_id = self.env['stock.picking.batch'].create({
                "picking_type_id": picking_ids[0].picking_type_id.id,
                "user_id": False,
                "state": "draft",
            })
        line_ids = self.env['stock.picking.to.pda.lines']
        for pick in picking_ids:
            line_ids |= self.env['stock.picking.to.pda.lines'].create({'picking_id': pick.id, 'sale_id': pick.sale_id.id, 'box_id': pick.box_id and pick.box_id.id or False})
        # return {'batch_id': batch_id.id, 'line_ids': [(6,0,line_ids.ids)], 'move_line_ids': [(6, 0, picking_ids.mapped('move_line_ids').ids)]}
        return {'picking_type_id': picking_type_id.id,
                'batch_id': batch_id and batch_id.id or False,
                'line_ids': [(6,0,line_ids.ids)],
                'move_line_ids': [(6, 0, picking_ids.mapped('move_line_ids').ids)]}

    @api.multi
    def attach_pickings(self):
        # use active_ids to add picking line to the selected batch
        self.ensure_one()


        if any(not x.box_id for x in self.line_ids.filtered(lambda x: x.picking_id.picking_type_id.code == 'outgoing')):
            raise ValidationError (_('All pickings must be assigned to box' ))

        if any(x.picking_id.state != 'assigned' for x in self.line_ids):
            raise ValidationError (_("All pickings must be 'assigned'" ))
        if not self.batch_id:
            pick = self.line_ids[0].picking_id
            vals = {'name': pick.name,
                    'picking_type_id': self.picking_type_id.id}
            self.batch_id = self.batch_id.create(vals)
        self.batch_id.state = 'in_progress'
        for line in self.line_ids:
            pick = line.picking_id
            pick.box_id = line.box_id
            pick.batch_id = self.batch_id
            pick.assign_removal_priority()
