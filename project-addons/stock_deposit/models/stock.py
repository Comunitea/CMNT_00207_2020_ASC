##############################################################################
#
#    Author: Santi Argüeso
#    Copyright 2014 Pexego Sistemas Informáticos S.L.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    @api.model
    def send_advise_email(self):
        deposits = self.search([('scheduled_date', '=', fields.Date.today())])
        # ~ mail_pool = self.env['mail.mail']
        # ~ mail_ids = self.env['mail.mail']
        template = self.env.ref('stock_deposit.stock_deposit_advise_partner', False)
        for deposit in deposits:
            ctx = dict(self._context)
            ctx.update({
                'default_model': 'stock.deposit',
                'default_res_id': deposit.id,
                'default_use_template': bool(template.id),
                'default_template_id': template.id,
                'default_composition_mode': 'comment',
                'mark_so_as_sent': True
            })
            composer_id = self.env['mail.compose.message'].with_context(
                ctx).create({})
            composer_id.with_context(ctx).send_mail()
            # ~ mail_id = template.send_mail(deposit.id)
            # ~ mail_ids += mail_pool.browse(mail_id)
        # ~ if mail_ids:
        # ~ mail_ids.send()



        return True


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def _action_done(self):
        res = super(StockMove, self)._action_done()

        deposit_obj = self.env['stock.deposit']
        for move in self:
            if move.sale_line_id.deposit and \
                    move.picking_type_id.code == "outgoing":
                formatted_date = datetime.strptime(time.strftime('%Y-%m-%d'),
                                                   "%Y-%m-%d")
                return_date = datetime.\
                    strftime(formatted_date + timedelta(days=15), "%Y-%m-%d")
                values = {
                    'move_id': move.id,
                    'delivery_date':
                    time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'return_date':
                    move.sale_line_id.deposit_date or
                    return_date,
                    'user_id':
                    move.sale_line_id.order_id.user_id.id,
                    'state': 'draft'
                }
                deposit_obj.create(values)
        return res


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _push_prepare_move_copy_values2(self, move_to_copy, new_date):
        company_id = self.company_id.id
        if not company_id:
            company_id = self.sudo().warehouse_id and self.sudo().warehouse_id.company_id.id or self.sudo().picking_type_id.warehouse_id.company_id.id
        new_move_vals = {
            'origin': move_to_copy.origin or move_to_copy.picking_id.name or "/",
            'location_id': move_to_copy.location_dest_id.id,
            'location_dest_id': self.location_id.id,
            'date': new_date,
            'date_expected': new_date,
            'company_id': company_id,
            'picking_id': False,
            'picking_type_id': self.picking_type_id.id,
            'propagate': self.propagate,
            'warehouse_id': self.warehouse_id.id,
        }
        return new_move_vals

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        if self.location_src_id.deposit_location and move_to_copy.partner_id.property_deposit_days:
            new_date = fields.Datetime.to_string(move_to_copy.date_expected + relativedelta(days=move_to_copy.partner_id.property_deposit_days))
            new_move_vals.update(date=new_date, date_expected=new_date)
        return new_move_vals

    def _get_stock_move_values(self, product_id, product_qty, product_uom,
                               location_id, name, origin, values, group_id):
        vals = super()._get_stock_move_values(
            product_id, product_qty, product_uom,
            location_id, name, origin, values, group_id)

        sale_line_id = vals.get('sale_line_id', False)
        if sale_line_id:
            sale_line_id =  self.env['sale.order.line'].browse(vals['sale_line_id'])
            if sale_line_id.deposit:
                picking_type_id = self.env['stock.picking.type'].\
                    search([('name', '=', u'Depósitos')])
                vals['location_dest_id'] = sale_line_id.order_id.partner_id.\
                    commercial_partner_id.property_stock_deposit.id
                if picking_type_id:
                    vals['picking_type_id'] = picking_type_id.id

        return vals
