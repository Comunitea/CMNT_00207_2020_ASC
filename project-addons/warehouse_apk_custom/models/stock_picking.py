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
        if mode == 'form':
            res += ['carrier_weight', 'carrier_packages']
        return res

    def auto_assign_batch_id(self):
        if self.batch_id:
            raise ValidationError ('El albarán {} ya está en el lote {}'.format(self.name, self.batch_id.name))
        batch_domain = self.picking_type_id.group_code.batch_domain or "[('picking_type_id', '=', self.picking_type_id.id)]"
        domain = eval(batch_domain)
        domain += [('state', 'in', ['assigned', 'draft']),
                   ('user_id', '=', False),
                   ('payment_on_delivery', '=', self.payment_on_delivery)]
        spb = self.env['stock.picking.batch']
        batch_id = spb.search(domain)
        if not batch_id:
            new_batch_vals = {
                'picking_type_id': self.picking_type_id.id,
                'name': self.name,
                'user_id': False,
                'partner_id': self.partner_id.id,
                'carrier_id': self.carrier_id.id,
                'state': 'draft',
                'picking_ids': [(6, 0, self.ids)],
                'payment_on_delivery': self.payment_on_delivery
            }
            batch_id = spb.create(new_batch_vals)
        else:
            self.write({'batch_id': batch_id.id})
        batch_id.assign_order_moves()
        return


    @api.depends('ready_to_send', 'move_type', 'move_lines.state', 'move_lines.picking_id')
    @api.one
    def _compute_state(self):
        super()._compute_state()
        if self.app_integrated:# and not self.batch_id and self.state=='assigned':
            self.check_apk_batch()

    @api.multi
    def check_apk_batch(self):
        for pick in self:
            if pick.state == 'assigned' and not pick.batch_id:
                #pick.auto_assign_batch_id()
                pass
            # elif self.state not in ['done', 'assigned'] and self.batch_id:
            #     if pick.batch_id.user_id:
            #         raise ValidationError(
            #             'No puedes cambiar el envío a almacén del albarán {} porque está en el batch {}'.format(
            #                 pick.name, pick.batch_id.name))
            #     batch_id = self.env['stock.picking.batch']
            #     batch_id |= pick.batch_id
            #     pick.batch_id = self.env['stock.picking.batch']
            #     if not batch_id.picking_ids:
            #         batch_id.unlink()

    @api.multi
    def write(self, vals):
        return super().write(vals=vals)

