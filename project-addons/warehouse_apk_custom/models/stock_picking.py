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
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)

class PickingTypeGroupCode(models.Model):
    _inherit = 'picking.type.group.code'

    batch_domain = fields.Char('Dominio para buscar batchs')
    batch_group_fields = fields.Many2many('ir.model.fields', domain="[('model_id', '=', 287)]")
    need_package = fields.Boolean('Paquetes', help="Si está marcado no permite validar con paquetes a 0")
    need_weight = fields.Boolean('Peso', help="Si está marcdo no permite validar con peso a 0.00")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    batch_id = fields.Many2one(
        domain="[('state', 'in', ('assigned', 'draft'))]",
    )

    def return_fields(self, mode='tree'):
        res = super().return_fields(mode=mode)
        res += ['carrier_id', 'team_id']

        if mode == 'form':
            res += ['carrier_weight', 'carrier_packages']
        return res

    def get_autoassign_pick_domain(self):
        domain = ['|', ('picking_type_id.group_code.app_integrated', '=', False),
                  '&', ('picking_type_id.group_code.app_integrated', '=', True), ('ready_to_send', '=', True),
                   ('batch_id', '=', False),
                   ('state', '=', 'assigned')]
        return domain

    def get_autoassign_batch_domain(self):
        batch_domain = self.picking_type_id.group_code.batch_domain or "[('picking_type_id', '=', self.picking_type_id.id)]"
        domain = eval(batch_domain)
        domain += [('state', 'in', ['assigned', 'draft']),
                   ('user_id', '=', False),
                   ('payment_on_delivery', '=', self.payment_on_delivery)]
        return domain

    @api.multi
    def cron_auto_assign_batch_id(self):
        domain = self.get_autoassign_pick_domain()
        for pick in self.env['stock.picking'].search(domain):
            pick.auto_assign_batch_id()

    def get_new_batch_values(self):
        return {
                'picking_type_id': self.picking_type_id.id,
                'name': self.name,
                'user_id': False,
                'partner_id': self.partner_id.id,
                'carrier_id': self.carrier_id.id,
                'team_id': self.team_id.id,
                'state': 'draft',
                'picking_ids': [(6, 0, self.ids)],
                'payment_on_delivery': self.payment_on_delivery,
            }

    def auto_assign_batch_id(self):

        if self.batch_id:
            raise ValidationError ('El albarán {} ya está en el lote {}'.format(self.name, self.batch_id.name))
        domain = self.get_autoassign_batch_domain()
        spb = self.env['stock.picking.batch']
        batch_id = spb.search(domain)
        if not batch_id:
            batch_id = spb.create(self.get_new_batch_values())

        if batch_id:
            self.write({'batch_id': batch_id.id})
            batch_id.assign_order_moves()
            _logger.info('Se mete en el batch {} el albarán {}'.format(batch_id.name, self.name))
        return

    @api.multi
    def check_apk_batch(self):
        domain = self.get_autoassign_pick_domain()
        domain += [('id', 'in', self.ids)]
        picks = self.env['stock.picking'].search(domain)
        if not picks:
            print('No hay nada para enviar')
        for pick in picks:

            pick.auto_assign_batch_id()
            print('Asigno {} a {}'. format(pick.name, pick.batch_id.name))


    @api.multi
    def write(self, vals):
        return super().write(vals=vals)

