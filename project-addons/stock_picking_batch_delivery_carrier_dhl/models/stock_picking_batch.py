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

import base64
import json
import random
import string
import time
from datetime import datetime, timedelta

import requests
import urllib3

from odoo import api, fields, models
from odoo.exceptions import UserError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class StockBatchPicking(models.Model):

    _inherit = "stock.picking.batch"

    @api.multi
    def compute_resquest_date(self):
        for delivery in self:
            calculated_picking_time = "{:%H:%M:%S}".format(
                datetime.now() + timedelta(hours=1)
            )
            picking_time = time.strftime(
                "%Y-%m-%dT{}%Z".format(calculated_picking_time), time.gmtime()
            )
            k = "{}:{}".format(
                time.strftime("%z", time.gmtime())[:3],
                time.strftime("%z", time.gmtime())[3:],
            )
            self.request_date = "{}{}".format(picking_time, k)

    request_date = fields.Char(
        "Requested Date", compute="compute_resquest_date"
    )

    def setHeaders(self):

        auth_data = "{}:{}".format(
            self.carrier_id.account_id.account,
            self.carrier_id.account_id.password,
        )
        auth_basic = "Basic " + str(
            base64.b64encode(auth_data.encode()).decode()
        )

        headers = {
            "authorization": auth_basic,
            "content-type": "application/json",
            "cache-control": "no-cache",
        }

        return headers

    def send_shipping(self):
        super(StockBatchPicking, self).send_shipping()
        if self.carrier_id.code == "DHL":
            headers = self.setHeaders()

            if not self.carrier_id.account_id:
                raise UserError("Delivery carrier has no account.")

            if self.carrier_id.account_id.test_enviroment:
                url = "{}ShipmentRequest".format(
                    self.carrier_id.account_id.service_test_url
                )
            else:
                url = "{}ShipmentRequest".format(
                    self.carrier_id.account_id.service_url
                )

            RequestedPackages = []
            cur_pack = 1
            while cur_pack <= self.carrier_packages:
                package_info = {
                    "@number": "{}".format(cur_pack),
                    "Weight": self.carrier_weight / self.carrier_packages,
                    "Dimensions": {"Length": 1.0, "Width": 1.0, "Height": 1.0},
                    "CustomerReferences": "{}".format(self.name.upper()),
                }
                RequestedPackages.append(package_info)
                cur_pack += 1

            payload = {
                "ShipmentRequest": {
                    "RequestedShipment": {
                        "ShipmentInfo": {
                            "DropOffType": "REGULAR_PICKUP"
                            if self.carrier_id.account_id.daily_picking
                            else "REQUEST_COURIER",
                            "ServiceType": "N"
                            if self.partner_id.country_id.code == "ES"
                            else "U"
                            if self.partner_id.country_id.intrastat
                            else "P",
                            "Account": "{}".format(
                                self.carrier_id.account_id.dhl_account
                            ),
                            "Currency": "EUR",
                            "UnitOfMeasurement": "SI",
                            "LabelType": self.carrier_id.account_id.file_format,
                            "PackagesCount": self.carrier_packages,
                            "LabelTemplate": self.carrier_id.account_id.dhl_label_template,
                        },
                        "ShipTimestamp": self.request_date,
                        "PaymentInfo": "DAP",
                        "InternationalDetail": {
                            "Commodities": {
                                "Description": "{}".format(self.name.upper()),
                            },
                            "Content": "DOCUMENTS"
                            if self.partner_id.country_id.code == "ES"
                            or self.partner_id.country_id.intrastat
                            else "NON_DOCUMENTS",
                        },
                        "Ship": {
                            "Shipper": {
                                "Contact": {
                                    "PersonName": "{}".format(
                                        self.user_id.name.upper()
                                        if self.user_id
                                        else self.env.user.company_id.name.upper()
                                    ),
                                    "CompanyName": "{}".format(
                                        self.env.user.company_id.name.upper()
                                    ),
                                    "PhoneNumber": "{}".format(
                                        self.env.user.company_id.phone
                                        or self.env.user.company_id.mobile
                                    ),
                                    "EmailAddress": self.env.user.company_id.email,
                                },
                                "Address": {
                                    "StreetLines": "{}".format(
                                        self.env.user.company_id.street
                                    ),
                                    "StreetLines2": "{}".format(
                                        self.env.user.company_id.street2
                                        or "N/A"
                                    ),
                                    "City": "{}".format(
                                        self.env.user.company_id.city.upper()
                                        if self.env.user.company_id.city.upper()
                                        else self.env.user.company_id.state_id.name.upper()
                                    ),
                                    "PostalCode": self.env.user.company_id.zip,
                                    "CountryCode": "{}".format(
                                        self.env.user.company_id.country_id.code
                                        or "ES"
                                    ),
                                },
                            },
                            "Recipient": {
                                "Contact": {
                                    "PersonName": "{}".format(
                                        self.partner_id.name.upper()
                                    ),
                                    "CompanyName": "{}".format(
                                        self.partner_id.parent_id.name.upper()
                                        if self.partner_id.parent_id
                                        else self.partner_id.name.upper()
                                    ),
                                    "PhoneNumber": "{}".format(
                                        self.partner_id.phone
                                        or self.partner_id.mobile
                                    ),
                                    "EmailAddress": "{}".format(
                                        self.partner_id.email
                                    ),
                                },
                                "Address": {
                                    "StreetLines": "{}".format(
                                        self.partner_id.street
                                    ),
                                    "StreetLines2": "{}".format(
                                        self.partner_id.street2 or "N/A"
                                    ),
                                    "City": "{}".format(
                                        self.partner_id.city.upper()
                                        if self.partner_id.city.upper()
                                        else self.partner_id.state_id.name.upper()
                                    ),
                                    "PostalCode": self.partner_id.zip,
                                    "CountryCode": "{}".format(
                                        self.partner_id.country_id.code
                                    ),
                                },
                            },
                        },
                        "Packages": {"RequestedPackages": RequestedPackages},
                    }
                }
            }

            try:
                r = requests.request(
                    "POST", url, data=json.dumps(payload), headers=headers
                )
                response = r.json()["ShipmentResponse"]

                if r.json()["ShipmentResponse"]:
                    response = r.json()["ShipmentResponse"]
                    if "ShipmentIdentificationNumber" not in response:
                        raise UserError(
                            "Error: {}".format(
                                response["Notification"][0]["Message"]
                            )
                        )
                    self.carrier_tracking_ref = response[
                        "ShipmentIdentificationNumber"
                    ]

                    if response["LabelImage"]:
                        if self.carrier_id.account_id.file_format == "PDF":
                            self.env["ir.attachment"].create(
                                {
                                    "name": "Label: {}".format(self.name),
                                    "type": "binary",
                                    "datas": response["LabelImage"][0][
                                        "GraphicImage"
                                    ],
                                    "datas_fname": "Label"
                                    + self.name
                                    + ".{}".format(
                                        response["LabelImage"][0][
                                            "LabelImageFormat"
                                        ]
                                    ),
                                    "store_fname": self.name,
                                    "res_model": self._name,
                                    "res_id": self.id,
                                    "mimetype": "application/x-pdf",
                                }
                            )
                        else:
                            self.env["ir.attachment"].create(
                                {
                                    "name": "Label: {}".format(self.name),
                                    "type": "binary",
                                    "datas": response["LabelImage"][0][
                                        "GraphicImage"
                                    ],
                                    "datas_fname": "Label"
                                    + self.name
                                    + ".{}".format(
                                        response["LabelImage"][0][
                                            "LabelImageFormat"
                                        ]
                                    ),
                                    "store_fname": self.name,
                                    "res_model": self._name,
                                    "res_id": self.id,
                                    "mimetype": "text/plain",
                                }
                            )
                        self.print_created_labels()
                    if response["PackagesResult"]:
                        shipment_reference = ""
                        for package in response["PackagesResult"][
                            "PackageResult"
                        ]:
                            shipment_reference += "{} ".format(
                                package["TrackingNumber"]
                            )
                        self.write({"shipment_reference": shipment_reference})
            except requests.exceptions.RequestException as e:
                raise UserError("Error: {}".format(e))


class StockPicking(models.Model):

    _inherit = "stock.picking"

    def get_message_reference(stringLength=8):
        lettersAndDigits = string.ascii_letters + string.digits
        return "".join(
            (random.choice(lettersAndDigits) for i in range(stringLength))
        )

    def check_shipment_status(self):
        if self.carrier_id.code == "DHL":
            headers = self.batch_id.setHeaders()

            if not self.carrier_id.account_id:
                raise UserError("Delivery carrier has no account.")

            if self.carrier_id.account_id.test_enviroment:
                url = "{}TrackingRequest".format(
                    self.carrier_id.account_id.service_test_url
                )
            else:
                url = "{}TrackingRequest".format(
                    self.carrier_id.account_id.service_url
                )

            payload = {
                "trackShipmentRequest": {
                    "trackingRequest": {
                        "TrackingRequest": {
                            "Request": {
                                "ServiceHeader": {
                                    "MessageTime": "{}".format(
                                        self.batch_id.request_date.replace(
                                            "GMT", ""
                                        )
                                    ),
                                    "MessageReference": "{}".format(
                                        self.get_message_reference(32)
                                    ),  #'212f797bf00a4afa9654cea8449c9779'
                                }
                            },
                            "AWBNumber": {
                                "ArrayOfAWBNumberItem": self.carrier_tracking_ref
                            },
                            "LevelOfDetails": "LAST_CHECKPOINT_ONLY",
                        }
                    }
                }
            }

            try:
                r = requests.request(
                    "POST", url, data=json.dumps(payload), headers=headers
                )
            except requests.exceptions.RequestException as e:
                raise UserError("Error: {}".format(e))

            response = r.json()["trackShipmentRequestResponse"]
            awbinfoitem = response["trackingResponse"]["TrackingResponse"][
                "AWBInfo"
            ]["ArrayOfAWBInfoItem"]
            if "ShipmentInfo" in awbinfoitem:
                delivery_status = shipment_info["ShipmentEvent"][
                    "ArrayOfShipmentEventItem"
                ]["ServiceEvent"]["EventCode"]
                if delivery_status == "OK":
                    self.delivered = True
            else:
                raise UserError(
                    "Error: {}".format(awbinfoitem["Status"]["ActionStatus"])
                )

        return super(StockPicking, self).check_shipment_status()
