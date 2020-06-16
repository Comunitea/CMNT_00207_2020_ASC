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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class DeliveryCarrier(models.Model):

    _inherit = 'delivery.carrier'

    carrier_type = fields.Selection(selection_add=[("dhl", "DHL Express")])


class CarrierAccount(models.Model):
    _inherit = 'carrier.account'

    delivery_carrier = fields.Selection(selection_add=[('dhl', 'DHL Express')])
    dhl_account = fields.Char('DHL Account')
    dhl_label_template = fields.Selection([
        ('ECOM26_84_A4_001', 'ECOM26_84_A4_001'),
        ('ECOM26_84_001', 'ECOM26_84_001'),
        ('ECOM_TC_A4', 'ECOM_TC_A4'),
        ('ECOM26_A6_002', 'ECOM26_A6_002'),
        ('ECOM26_84CI_001', 'ECOM26_84CI_001'),
        ('ECOM_A4_RU_002', 'ECOM_A4_RU_002'),
        ('ECOM26_A6_002', 'ECOM26_A6_002'),
        ('ECOM26_84CI_002', 'ECOM26_84CI_002'),
        ('ECOM26_84CI_003', 'ECOM26_84CI_003')
    ], default="ECOM26_84_001")
    daily_picking = fields.Boolean(string="Daily Picking", default=True)

    @api.onchange('file_format')
    def onchange_file_format(self):
        for account in self:
            if account.delivery_carrier == 'dhl' and self.file_format not in ('PDF', 'ZPL'):
                raise ValidationError(
                    _('The carrier DHL only admits PDF or ZPL format.'))