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
from odoo.exceptions import UserError
from base64 import b64decode

class StockBatchPicking(models.Model):

    _inherit = 'stock.picking.batch'

    carrier_id = fields.Many2one(comodel_name='delivery.carrier', string='Carrier')
    carrier_code = fields.Char(related="carrier_id.code")
    tracking_code = fields.Char('Tracking Code')
    shipment_reference = fields.Char('Shipment Reference')
    payment_on_delivery = fields.Boolean('Payment on delivery', compute="_compute_payment_on_delivery")

    @api.multi
    def _compute_payment_on_delivery(self):
        for batch in self:
            if any(x.sale_id.payment_mode_id.payment_on_delivery for x in batch.picking_ids):
                self.payment_on_delivery = True

    @api.multi
    def write(self, vals):
        res = super().write(vals)
        if vals.get('tracking_code', False):
            self.onchange_tracking_code()
        return res

    @api.onchange('tracking_code')
    def onchange_tracking_code(self):
        if self.tracking_code:
            for pick in self.picking_ids:
                pick.write({
                    'carrier_tracking_ref': self.tracking_code
                })

    @api.multi
    def action_transfer(self):
        self.send_shipping()
        res = super(StockBatchPicking, self).action_transfer()
        return res

    def send_shipping(self):
        self.check_delivery_address()
        return True

    def track_request(self):
        return True
    
    def check_delivery_address(self):
        if not self.partner_id.state_id:
            raise UserError("Partner id addres is not complete (State missing).")
        if not self.partner_id.country_id:
            raise UserError("Partner id addres is not complete (Contry missing).")
        if not self.partner_id.email:
            raise UserError("Partner id addres is not complete (Email missing).")
        if not self.partner_id.zip:
            raise UserError("Partner id addres is not complete (Zip code missing).")
        if not self.env.user.company_id.state_id:
            raise UserError("Company id addres is not complete (State missing).")
        if not self.env.user.company_id.state_id:
            raise UserError("Company id addres is not complete (State missing).")

    def print_created_labels(self):
        self.ensure_one()
        
        if not self.carrier_id.account_id.printer:
            raise UserError('Printer not defined')
        labels =  self.env['ir.attachment'].search([
            ('res_id', '=', self.id),
            ('res_model', '=', self._name)
        ])
        for label in labels:
            self.carrier_id.account_id.printer.print_document(
                None, b64decode(label.datas), doc_format="raw"
            )


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.multi
    def send_to_shipper(self):
        if not self.batch_id:
            super().send_to_shipper()

    def onchange_partner_id_or_carrier_id(self):
        return True


class CarrierAccount(models.Model):
    _inherit = 'carrier.account'

    delivery_carrier = fields.Selection([('none', 'None')])
    
