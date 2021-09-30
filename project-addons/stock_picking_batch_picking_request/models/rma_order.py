##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2021 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
#    Vicente Ángel Gutiérrez <vicente@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class RmaOrder(models.Model):
    _inherit = "rma.order"

    def action_rma_approve(self):
        res = super(RmaOrder, self).action_rma_approve()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        spain_carrier_id = get_param('stock_picking_batch_picking_request.spain_carrier_id')
        europe_carrier_id = get_param('stock_picking_batch_picking_request.europe_carrier_id')

        if not spain_carrier_id or not europe_carrier_id:
            raise UserError("Picking request carriers not configured.")

        for rma in self:
            if rma.operation_type == 'rma':
                picking_ids = []
                for line in rma.rma_line_ids:
                    for move in line.move_ids:
                        if move.location_dest_id.usage == 'internal':
                            picking_ids.append(move.picking_id)
                        else:
                            if line.customer_to_supplier:
                                picking_ids.append(move.picking_id)

                if picking_ids:
                    for pick in picking_ids:
                        pick.action_assign()
                        pick.auto_assign_batch_id()
                
                        if pick.batch_id and pick.batch_id.partner_id and pick.batch_id.partner_id.country_id:
                            pick.batch_id.carrier_id = int(spain_carrier_id) if pick.batch_id.partner_id.country_id.code.upper() == 'ES' else int(europe_carrier_id)
                            pick.batch_id.send_shipping()
        return res