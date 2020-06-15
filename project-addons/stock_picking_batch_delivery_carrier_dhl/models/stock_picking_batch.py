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
import requests 
import base64
import urllib
from requests.auth import HTTPBasicAuth
import urllib3
import json
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from odoo.exceptions import UserError
from datetime import datetime, timezone, timedelta
from time import gmtime, strftime
import time
import pytz
import random, string

class StockBatchPicking(models.Model):

    _inherit = 'stock.picking.batch'

    @api.multi
    @api.depends('picking_time')
    def compute_resquest_date(self):
        for delivery in self:
            picking_time = time.strftime("%Y-%m-%dT{}%Z".format(self.picking_time), time.gmtime())
            k = "{}:{}".format(time.strftime("%z", time.gmtime())[:3], time.strftime("%z", time.gmtime())[3:])
            self.request_date = "{}{}".format(
                picking_time,
                k
            )

    request_date = fields.Char('Requested Date', compute="compute_resquest_date")
    daily_picking = fields.Boolean(string="Daily Picking", default=True)
    picking_time = fields.Char(string="Picking time", help="Format: HH:MM:SS", default="19:00:00")


    def setHeaders(self):

        auth_data = url = "{}:{}".format(
            self.carrier_id.account_id.account,
            self.carrier_id.account_id.password
        )
        auth_basic = "Basic " + str(base64.b64encode(auth_data.encode()).decode())

        headers = {
            'authorization': auth_basic,
            'content-type': "application/json",
            'cache-control': "no-cache" 
        }

        return headers

    def send_shipping(self):
        if self.carrier_id.code == 'DHL':
            headers = self.setHeaders()

            if not self.carrier_id.account_id:
                raise UserError("Delivery carrier has no account.")

            if self.carrier_id.account_id.test_enviroment:
                url = "{}ShipmentRequest".format(
                    self.env['ir.config_parameter'].get_param("stock_picking_batch_delivery_carrier_dhl.api_test_url")
                )
            else:
                url = "{}ShipmentRequest".format(
                    self.env['ir.config_parameter'].get_param("stock_picking_batch_delivery_carrier_dhl.api_url")
                )

            RequestedPackages = []
            cur_pack = 1
            while cur_pack <= self.carrier_packages:
                package_info = {
                    "@number":"{}".format(cur_pack),
                    "Weight":self.carrier_weight/self.carrier_packages,
                    "Dimensions": {
                        "Length":self.length,
                        "Width":self.width,
                        "Height":self.height
                    },
                    "CustomerReferences":"{}".format(self.name.upper())
                }
                RequestedPackages.append(package_info)
                cur_pack+=1
                
            payload = {
                "ShipmentRequest": {
                    "RequestedShipment": {
                        "ShipmentInfo": {
                            "DropOffType": "REGULAR_PICKUP" if self.daily_picking else "REQUEST_COURIER",
                            "ServiceType":"N" if self.partner_id.country_id.code == 'ES' else "U" if self.partner_id.country_id.intrastat else "P",
                            "Account":"{}".format(self.carrier_id.account_id.dhl_account),
                            "Currency":"EUR",
                            "UnitOfMeasurement":"SI",
                            "LabelType":self.carrier_id.account_id.file_format,
                            "PackagesCount":self.carrier_packages,
                            "LabelTemplate":self.carrier_id.account_id.dhl_label_template
                        },
                        "ShipTimestamp":self.request_date,
                        "PaymentInfo":"DAP",
                        "InternationalDetail": {
                            "Commodities": {
                                "NumberOfPieces":1.0,
                                "Description":"{}".format(self.name.upper()),
                                "CountryOfManufacture":"",
                                "Quantity":"",
                                "UnitPrice":"",
                                "CustomsValue":7.9
                            },
                            "Content":"DOCUMENTS" if self.partner_id.country_id.code == 'ES'or self.partner_id.country_id.intrastat else "NON_DOCUMENTS"
                        },
                        "Ship": {
                            "Shipper": {
                                "Contact": {
                                    "PersonName": "{}".format(self.user_id.name.upper() if self.user_id else "N/A"),
                                    "CompanyName":"{}".format(self.env.user.company_id.name.upper()),
                                    "PhoneNumber":"{}".format(self.env.user.company_id.phone or self.env.user.company_id.mobile or "N/A"),
                                    "EmailAddress":"{}".format(self.env.user.company_id.email or "N/A")
                                },
                                "Address": {
                                    "StreetLines":"{}".format(self.env.user.company_id.street or "N/A"),
                                    "StreetLines2":"{}".format(self.env.user.company_id.street2 or "N/A"),
                                    "City":"{}".format(self.env.user.company_id.state_id.name.upper() or "N/A"),
                                    "PostalCode":self.env.user.company_id.zip or "N/A",
                                    "CountryCode":"{}".format(self.env.user.company_id.country_id.code or "ES")
                                }
                            },
                            "Recipient": {
                                "Contact": {
                                    "PersonName":"{}".format(self.partner_id.name.upper()),
                                    "CompanyName":"{}".format(self.partner_id.parent_id.name.upper() if self.partner_id.parent_id else "N/A"),
                                    "PhoneNumber":"{}".format(self.partner_id.phone or self.partner_id.mobile or "N/A"),
                                    "EmailAddress":"{}".format(self.partner_id.email or "N/A")
                                },
                                "Address": {
                                    "StreetLines":"{}".format(self.partner_id.street or "N/A"),
                                    "StreetLines2":"{}".format(self.partner_id.street2 or "N/A"),
                                    "City":"{}".format(self.partner_id.state_id.name.upper() or "N/A"),
                                    "PostalCode":self.partner_id.zip or "N/A",
                                    "CountryCode":"{}".format(self.partner_id.country_id.code or "ES")
                                }
                            }
                        },
                        "Packages": {
                            "RequestedPackages": RequestedPackages
                        }
                    }
                }
            }

            try:
                print("TEST")
                r = requests.request("POST", url, data=json.dumps(payload), headers=headers)
                print(r)
            except requests.exceptions.RequestException as e:
                raise UserError("Error: {}".format(e))

            print(r.json())
            response = r.json()['ShipmentResponse']

            if r.json()['ShipmentResponse']:
                response = r.json()['ShipmentResponse']
                if 'ShipmentIdentificationNumber' not in response:
                    raise UserError("Error: {}".format(response['Notification'][0]['Message']))
                self.shipment_reference = response['ShipmentIdentificationNumber']
                if response['LabelImage']:
                    attatchment = self.env['ir.attachment'].create({
                        'name': "Label: {}".format(self.name),
                        'type': 'binary',
                        'datas': response['LabelImage'][0]['GraphicImage'],
                        'datas_fname': 'Label' + self.name + '.{}'.format(response['LabelImage'][0]['LabelImageFormat']),
                        'store_fname': self.name,
                        'res_model': self._name,
                        'res_id': self.id,
                        'mimetype': 'application/x-pdf'
                    })
                if response['PackagesResult']:
                    tracking_code = ''
                    for package in response['PackagesResult']['PackageResult']:
                        tracking_code += "{} ".format(package['TrackingNumber'])
                    self.write({
                        'delivery_status': 'R',
                        'tracking_code': tracking_code
                    })
                    print("actualziando tracking_code {}".format(tracking_code))
                    print(self.tracking_code)

            print(r)
            print(r.text)
        res = super(StockBatchPicking, self).send_shipping()

    
    def cancel_shipment(self):
        if self.carrier_id.code == 'DHL':
            headers = self.setHeaders()

            if not self.carrier_id.account_id:
                raise UserError("Delivery carrier has no account.")

            if self.carrier_id.account_id.test_enviroment:
                url = "{}DeleteShipment".format(
                    self.env['ir.config_parameter'].get_param("stock_picking_batch_delivery_carrier_dhl.api_test_url")
                )
            else:
                url = "{}DeleteShipment".format(
                    self.env['ir.config_parameter'].get_param("stock_picking_batch_delivery_carrier_dhl.api_url")
                )

            payload = {
                "DeleteRequest": {
                    "PickupDate":"{}".format(time.strftime("%Y-%m-%d")),
                    "PickupCountry":"{}".format(self.env.user.company_id.country_id.code or "ES"),
                    "DispatchConfirmationNumber":self.shipment_reference,
                    "RequestorName":"{}".format(self.env.user.company_id.name.upper())
                }
            }

            try:
                r = requests.request("POST", url, data=json.dumps(payload), headers=headers)
            except requests.exceptions.RequestException as e:
                raise UserError("Error: {}".format(e))
            
            response = r.json()['DeleteResponse']

            if response['Response']:
                self.tracking_code = ''
                self.shipment_reference = ''
                attatchment_id = self.env['ir.attachment'].search([
                    ('name', '=', "Label: {}".format(self.name)),
                    ('store_fname', '=', self.name),
                    ('res_id', '=', self.id),
                    ('res_model', '=', self._name),
                    ('mimetype', '=', 'application/x-pdf')
                ]).unlink()
        res = super(StockBatchPicking, self).cancel_shipment()


    def track_request(self):
        if self.carrier_id.code == 'DHL':
            headers = self.setHeaders()

            if not self.carrier_id.account_id:
                raise UserError("Delivery carrier has no account.")

            if self.carrier_id.account_id.test_enviroment:
                url = "{}TrackingRequest".format(
                    self.env['ir.config_parameter'].get_param("stock_picking_batch_delivery_carrier_dhl.api_test_url")
                )
            else:
                url = "{}TrackingRequest".format(
                    self.env['ir.config_parameter'].get_param("stock_picking_batch_delivery_carrier_dhl.api_url")
                )

            payload = {
                "trackShipmentRequest": {
                    "trackingRequest": {
                        "TrackingRequest": {
                            "Request": {
                                "ServiceHeader": {
                                    "MessageTime": "{}".format(self.request_date.replace('GMT', '')),
                                    "MessageReference": '212f797bf00a4afa9654cea8449c9779' # Meterle un random a esto
                                }
                            },
                            "ReferenceQuery": {
                                "ShipperAccountNumber": "{}".format(self.carrier_id.account_id.dhl_account),
                                "ShipmentReferences": {
                                    "ShipmentReference": self.shipment_reference
                                }
                            },
                            "LevelOfDetails": "LAST_CHECKPOINT_ONLY"
                        }
                    }
                }
            }

            try:
                r = requests.request("POST", url, data=json.dumps(payload), headers=headers)
            except requests.exceptions.RequestException as e:
                raise UserError("Error: {}".format(e))

            print(r)
            print(r.text)
            response = r.json()['trackShipmentRequestResponse']
            awbinfoitem = response['trackingResponse']['TrackingResponse']['AWBInfo']['ArrayOfAWBInfoItem']
            if 'ShipmentInfo' in awbinfoitem:
                self.delivery_status = shipment_info['ShipmentEvent']['ArrayOfShipmentEventItem']['ServiceEvent']['EventCode']
            else:
                raise UserError("Error: {}".format(awbinfoitem['Status']['ActionStatus']))
            
            
        res = super(StockBatchPicking, self).track_request()
