##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2020 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
#    Vicente Ángel Gutiérrez <vicente@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See thefire
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api, _
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES

class StockBatchPicking(models.Model):
    _inherit = "stock.picking.batch"
    _order = "priority desc, date asc, id desc"

    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority',
        compute='_compute_priority', inverse='_set_priority', store=True,
        # default='1', required=True,  # TDE: required, depending on moves ? strange
        index=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Priority for this picking. Setting manually a value here would set it as priority for all the moves")

    @api.one
    @api.depends('move_lines.priority')
    def _compute_priority(self):
        if self.mapped('move_lines'):
            priorities = [priority for priority in self.mapped('move_lines.priority') if priority] or ['1']
            self.priority = max(priorities)
        else:
            self.priority = '1'
    
    @api.one
    def _set_priority(self):
        self.move_lines.write({'priority': self.priority})
