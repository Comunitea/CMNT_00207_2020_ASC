##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2019 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
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

from odoo import api, models, fields
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'
    _order = "name asc"

    carrier_weight = fields.Float(default=0)
    carrier_packages = fields.Integer(default=0)
    carrier_id = fields.Many2one('delivery.carrier', 'Carrier', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string="Empresa")
    picking_ids = fields.One2many(
        string='Pickings',
        readonly=True,
        states={'draft': [('readonly', False)], 'assigned': [('readonly', False)]},
        help='List of picking managed by this batch.',
    )
    team_id = fields.Many2one('crm.team')

    @api.model
    def get_wh_code_filter(self):
        wh_code_ids = ['', 'draft', 'waiting', 'confirmed', 'assigned', 'done', 'cancel']
        return wh_code_ids

    @api.model
    def button_validate_apk(self, vals):

        batch_id = self.browse(vals.get('id', False))
        if not batch_id:
            raise ValidationError("No se ha encontrado el albarán ")
        if batch_id.picking_type_id.group_code:
            g_code = batch_id.picking_type_id.group_code
            if g_code.need_weight and batch_id.carrier_weight == 0.00:
                raise ValidationError("Rellena el peso del albarán")
            if g_code.need_package and batch_id.carrier_packages == 0:
                raise ValidationError("Rellena el número de bultos")
        return super().button_validate_apk(vals)

    def return_fields(self, mode='tree'):
        res = super().return_fields(mode=mode)
        res += ['carrier_id', 'team_id']
        if mode == 'form':
            res += ['carrier_weight', 'carrier_packages']
        return res

    def get_model_object(self, values={}):

        res = super().get_model_object(values=values)
        picking_id = self
        if values.get('view', 'tree') == 'tree':
            return res
        if picking_id:
            picking_id.state == 'in_progress'
            picking_id.user_id = self.env.user
        if not picking_id:
            domain = values.get('domain', [])
            limit = values.get('limit', 1)
            move_id = self.search(domain, limit)
            if not picking_id or len(picking_id) != 1:
                return res
        values = {'domain': self.get_move_domain_for_picking(values.get('filter_moves', 'Todos'), picking_id)}
        res['move_lines'] = self.env['stock.move'].get_model_object(values)
        #print ("------------------------------Move lines")
        #pprint.PrettyPrinter(indent=2).pprint(res['move_lines'])
        return res