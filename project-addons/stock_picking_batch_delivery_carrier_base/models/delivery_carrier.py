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

from odoo import fields, models, api


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    service_code = fields.Many2one(
        "delivery.carrier.service", string="Carrier service code"
    )
    needs_signature = fields.Boolean()


class CarrierAccount(models.Model):
    _inherit = "carrier.account"

    service_url = fields.Char(string="Webservice URL")
    service_test_url = fields.Char(string="Webservice TEST URL")
    carrier_services = fields.One2many("delivery.carrier.service", "account_id")


class DeliveryCarrierService(models.Model):

    _inherit = "delivery.carrier.service"

    account_id = fields.Many2one("carrier.account")
