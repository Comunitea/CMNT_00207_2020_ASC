# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class RmaOrder(models.Model):
    _inherit = "rma.order"

    delivery_tag = fields.Binary(attachment=True, copy=False)
    delivery_address_id = fields.Many2one('res.partner')

    def action_rma_approve(self):
        return self.rma_line_ids.action_rma_approve()

    @api.multi
    def _compute_in_shipment_count(self):
        for rec in self:
            picking_ids = []
            for line in rec.rma_line_ids:
                for move in line.move_ids:
                    if move.location_dest_id.usage == 'internal':
                        picking_ids.append(move.picking_id.id)
                    else:
                        if line.customer_to_supplier:
                            picking_ids.append(move.picking_id.id)
            shipments = list(set(picking_ids))
            rec.in_shipment_count = len(shipments)

    @api.multi
    def _compute_out_shipment_count(self):
        picking_ids = []
        for rec in self:
            for line in rec.rma_line_ids:
                for move in line.move_ids:
                    if move.location_dest_id.usage in ('supplier', 'customer'):
                        if not line.customer_to_supplier:
                            picking_ids.append(move.picking_id.id)
            shipments = list(set(picking_ids))
            rec.out_shipment_count = len(shipments)
