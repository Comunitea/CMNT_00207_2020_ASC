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

_logger = logging.getLogger(__name__)

class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    carrier_weight = fields.Float()
    carrier_packages = fields.Integer(default=1)
    carrier_id = fields.Many2one('delivery.carrier', 'Carrier', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string="Empresa")
    picking_ids = fields.One2many(
        string='Pickings',
        readonly=True,
        states={'draft': [('readonly', False)], 'assigned': [('readonly', False)]},
        help='List of picking managed by this batch.',
    )

    def return_fields(self, mode='tree'):
        res = super().return_fields(mode=mode)
        if mode == 'form':
            res += ['carrier_weight', 'carrier_packages']
        return res
