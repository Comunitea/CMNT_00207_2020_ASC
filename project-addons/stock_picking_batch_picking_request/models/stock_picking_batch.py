##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2021 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
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

import logging
import base64
import requests
import json
from datetime import timedelta
import time

from odoo import models, _, fields
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

# Zeep debug

#import logging.config

""" logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(name)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'zeep.transports': {
            'level': 'DEBUG',
            'propagate': True,
            'handlers': ['console'],
        },
    }
}) """

class StockBatchPicking(models.Model):

    _inherit = "stock.picking.batch"

    carrier_dispatch_ref = fields.Char(string='Dispatch confirmation number')    

    def compute_picking_request_weight(self):
        weight = 0.0
        for move_line in self.move_line_ids.filtered('product_qty'):
            if not move_line.product_id:
                continue
            move = move_line.move_id
            qty = move.product_uom._compute_quantity(
                move_line.product_qty, move_line.product_id.uom_id,
            )
            weight += (move_line.product_id.weight or 0.0) * qty

        if weight <= 0.0:
            return 1

        return weight

    def send_shipping(self):

        def compute_timestamp_format(date):
            calculated_picking_time = "{:%Y-%m-%d}T{:%H:%M:%S}".format(date, date)
            picking_time = time.strftime(
                "{}%Z".format(calculated_picking_time), time.gmtime()
            )
            k = "{}:{}".format(
                time.strftime("%z", time.gmtime())[:3],
                time.strftime("%z", time.gmtime())[3:],
            )
            return "{}{}".format(picking_time, k)

        carrier_packages = self.carrier_packages if self.carrier_packages != 0 else 1
        carrier_weight = self.compute_picking_request_weight()

        self.check_delivery_address()
        if self.carrier_id.code == "MRW" and self.picking_type_id.code == 'incoming':

            # A REVISAR SI VIENEN AL CREAR UNO
            if not self.user_id:
                self.user_id = self.env['res.users'].browse(self.env.uid)
            if not self.partner_id:
                self.partner_id = self.picking_ids.mapped('partner_id')[0]

            if self.carrier_id.account_id.mrw_rma_delivery_partner_id:
                delivery_partner_id = self.carrier_id.account_id.mrw_rma_delivery_partner_id
            else:
                raise UserError("RMA delivery partner for MRW is not configured.")

            if not self.carrier_id.account_id:
                raise UserError("Delivery carrier has no account.")

            rma_id = self.picking_ids.move_lines.mapped('rma_line_id').rma_id

            if not rma_id:
                raise UserError("There is no rma_id.")

            client, history = self.create_client()

            if client:

                try:

                    headers = self.setMRWHeaders(client)

                    notices = []
                    if self.carrier_id.account_id.mrw_phone_notification:
                        phone_notification = {
                            "NotificacionRequest": {
                                "CanalNotificacion": "2",
                                "TipoNotificacion": self.carrier_id.account_id.mrw_notice_type,
                                "MailSMS": self.partner_id.phone
                                or self.partner_id.mobile
                                or self.partner_id.commercial_partner_id.phone
                                or self.partner_id.commercial_partner_id.mobile,
                            }
                        }
                        notices.append(phone_notification)

                    if self.carrier_id.account_id.mrw_mail_notification:
                        mail_notification = {
                            "NotificacionRequest": {
                                "CanalNotificacion": "1",
                                "TipoNotificacion": self.carrier_id.account_id.mrw_notice_type,
                                "MailSMS": self.partner_id.email
                                or self.partner_id.commercial_partner_id.email,
                            }
                        }
                        notices.append(mail_notification)

                    TransmEnvio = {
                        "request": {
                            "DatosRecogida": {
                                "Direccion": {
                                    "Via": "{} {}".format(
                                        self.partner_id.street or "",
                                        self.partner_id.street2 or "",
                                    ),
                                    "CodigoPostal": self.partner_id.zip.replace(
                                        " ", ""
                                    )[:4]
                                    if self.partner_id.country_id.code == "PT"
                                    else self.partner_id.zip.zfill(5)
                                    if self.partner_id.country_id.code == "AD"
                                    else self.partner_id.zip,
                                    "Poblacion": self.partner_id.city,
                                    "Provincia": self.partner_id.state_id.name,
                                },
                                "Nif": self.partner_id.vat,
                                "Nombre": self.partner_id.name,
                                "Telefono": self.partner_id.phone
                                or self.partner_id.mobile
                                or self.partner_id.commercial_partner_id.phone
                                or self.partner_id.commercial_partner_id.mobile
                                or "",
                                "Horario": {
                                    "Rangos": {
                                        "HorarioRangoRequest": {
                                            "Desde": rma_id.pickup_time.strftime("%H:%M"),
                                            "Hasta": (rma_id.pickup_time + timedelta(hours=3)).strftime("%H:%M"),
                                        },
                                    },
                                },
                                "Observaciones": "{}".format(self.delivery_note),
                            },
                            "DatosEntrega": {
                                "Direccion": {
                                    "Via": "{} {}".format(
                                        delivery_partner_id.street or "",
                                        delivery_partner_id.street2 or "",
                                    ),
                                    "CodigoPostal": delivery_partner_id.zip.replace(
                                        " ", ""
                                    )[:4]
                                    if delivery_partner_id.country_id.code == "PT"
                                    else delivery_partner_id.zip.zfill(5)
                                    if delivery_partner_id.country_id.code == "AD"
                                    else delivery_partner_id.zip,
                                    "Poblacion": delivery_partner_id.city,
                                    "Provincia": delivery_partner_id.state_id.name,
                                },
                                "Nif": delivery_partner_id.vat,
                                "Nombre": delivery_partner_id.name,
                                "Telefono": delivery_partner_id.phone
                                or delivery_partner_id.mobile
                                or "",
                            },
                            "DatosServicio": {
                                "Fecha": rma_id.pickup_time.strftime("%d/%m/%Y"),
                                #"Fecha": datetime.now().strftime(
                                #    "%d/%m/%Y"
                                #),
                                "Referencia": self.name,
                                "CodigoServicio": self.service_code.carrier_code,
                                "Frecuencia": self.carrier_id.account_id.mrw_frequency
                                if self.service_code.carrier_code == "0005"
                                else "",
                                "NumeroBultos": carrier_packages,
                                "Peso": round(carrier_weight),
                                "EntregaSabado": self.carrier_id.account_id.mrw_saturday_delivery,
                                "Entrega830": self.carrier_id.account_id.mrw_830_delivery,
                                "Gestion": self.carrier_id.account_id.mrw_delivery_hangle,
                                "ConfirmacionInmediata": self.carrier_id.account_id.mrw_instant_notice,
                                "Reembolso": self.carrier_id.account_id.mrw_delivery_pdo
                                if self.payment_on_delivery
                                else "N",
                                "ImporteReembolso": "{}".format(self.pdo_quantity).replace(".", ",")
                                if self.carrier_id.account_id.mrw_delivery_pdo != "N"
                                and self.payment_on_delivery
                                else "",
                                "TipoMercancia": self.carrier_id.account_id.mrw_goods_type
                                if self.partner_id.country_id.code != "ES"
                                else "",
                                "Notificaciones": notices,
                            },
                        }
                    }

                    res = client.service.TransmEnvio(
                        **TransmEnvio, _soapheaders=[headers]
                    )
                except Exception as e:
                    raise AccessError(_("Access error message: {}").format(e))

                if res["Estado"] == "0":
                    raise AccessError(_("Error message: {}").format(res["Mensaje"]))
                elif res["Estado"] == "1":

                    self.write(
                        {
                            "carrier_tracking_ref": res["NumeroEnvio"],
                            "shipment_reference": res["NumeroSolicitud"],
                        }
                    )

                    try:
                        label = self.get_carrier_label(
                            client, headers, res["NumeroEnvio"]
                        )
                    except Exception as e:
                        _logger.error(
                            _(
                                "Connection error: {}, while trying to retrieve the label."
                            ).format(e)
                        )
                        return

                    if label["Estado"] == "1":
                        file_b64 = base64.b64encode(label["EtiquetaFile"])
                        self.env["ir.attachment"].create(
                            {
                                "name": "Label: {}".format(self.name),
                                "type": "binary",
                                "datas": file_b64,
                                "datas_fname": "Label" + self.name + ".pdf",
                                "store_fname": self.name,
                                "res_model": self._name,
                                "res_id": self.id,
                                "mimetype": "application/x-pdf",
                            }
                        )
                        # rma
                        rma_id.delivery_tag = file_b64
                    elif label["Estado"] == "0":
                        raise AccessError(
                            _("Error while trying to retrieve the label: {}").format(
                                label["Mensaje"]
                            )
                        )
                    else:
                        raise AccessError(_("Error while trying to retrieve the label"))
                else:
                    raise AccessError(_("Unknown error with the SOAP connection."))

            else:
                raise AccessError(_("Not possible to establish a client."))

        elif self.carrier_id.code == "DHL" and self.picking_type_id.code == 'incoming':

            # A REVISAR SI VIENEN AL CREAR UNO
            if not self.user_id:
                self.user_id = self.env['res.users'].browse(self.env.uid)
            if not self.partner_id:
                self.partner_id = self.picking_ids.mapped('partner_id')[0]

            if self.picking_type_id.warehouse_id and self.picking_type_id.warehouse_id.partner_id:
                delivery_partner_id = self.picking_type_id.warehouse_id.partner_id
            else:
                raise UserError("Picking type missing warehouse or partner.")

            if not self.carrier_id.account_id:
                raise UserError("Delivery carrier has no account.")

            rma_id = self.picking_ids.move_lines.mapped('rma_line_id').rma_id

            if not rma_id:
                raise UserError("There is no rma_id.")

            headers = self.setHeaders()

            if self.carrier_id.account_id.test_enviroment:
                url = "{}ShipmentRequest".format(
                    self.carrier_id.account_id.service_test_url
                )
            else:
                url = "{}ShipmentRequest".format(self.carrier_id.account_id.service_url)

            RequestedPackages = []
            cur_pack = 1
            while cur_pack <= carrier_packages:
                package_info = {
                    "@number": "{}".format(cur_pack),
                    "Weight": round(carrier_weight / carrier_packages, 2),
                    "Dimensions": {"Length": 1.0, "Width": 1.0, "Height": 1.0},
                    "CustomerReferences": "{}".format(self.name.upper()),
                }
                RequestedPackages.append(package_info)
                cur_pack += 1

            payload = {
                "ShipmentRequest": {
                    "RequestedShipment": {
                        "ShipmentInfo": {
                            "DropOffType": "REQUEST_COURIER",
                            "ServiceType": self.service_code.carrier_code,
                            "Account": "{}".format(
                                self.carrier_id.account_id.dhl_impex_account
                            ),
                            "Currency": "EUR",
                            "UnitOfMeasurement": "SI",
                            "LabelType": "PDF",
                            "PackagesCount": carrier_packages,
                            "LabelTemplate": 'ECOM26_84_A4_001',
                        },
                        "ShipTimestamp": compute_timestamp_format(rma_id.pickup_time),
                        "PickupLocationCloseTime" : (rma_id.pickup_time + timedelta(hours=3)).strftime("%H:%M"),
                        "SpecialPickupInstruction" : "Pickup from {}".format(rma_id.pickup_time),
                        "PickupLocation": self.delivery_note or "N/A",
                        "PaymentInfo": "DAP",
                        "InternationalDetail": {
                            "Commodities": {
                                "Description": "{}".format(self.name.upper())
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
                                        self.partner_id.name.upper()
                                    ),
                                    "CompanyName": "{}".format(
                                        self.partner_id.parent_id.name.upper() if self.partner_id.parent_id else self.partner_id.name.upper()
                                    ),
                                    "PhoneNumber": "{}".format(
                                        self.partner_id.phone if self.partner_id.phone else self.partner_id.mobile if self.partner_id.mobile else "",
                                    ),
                                    "EmailAddress": self.partner_id.email or "",
                                },
                                "Address": {
                                    "StreetLines": "{}".format(
                                        self.partner_id.street
                                    ),
                                    "StreetLines2": "{}".format(
                                        self.partner_id.street2 or "N/A"
                                    ),
                                    "StreetLines3": "{}".format(
                                        self.delivery_note or "N/A"
                                    ),
                                    "City": "{}".format(
                                        self.partner_id.city.upper()
                                    ),
                                    "PostalCode": self.partner_id.zip,
                                    "CountryCode": "{}".format(
                                        self.partner_id.country_id.code or "ES"
                                    ),
                                },
                            },
                            "Recipient": {
                                "Contact": {
                                    "PersonName": "{}".format(
                                        self.user_id.name.upper()
                                        if self.user_id
                                        else delivery_partner_id.name.upper()
                                    ),
                                    "CompanyName": "{}".format(
                                        delivery_partner_id.name.upper()
                                    ),
                                    "PhoneNumber": "{}".format(
                                        delivery_partner_id.phone
                                        or delivery_partner_id.mobile
                                    ),
                                    "EmailAddress": "{}".format(
                                        delivery_partner_id.email
                                        or ""
                                    ),
                                },
                                "Address": {
                                    "StreetLines": "{}".format(delivery_partner_id.street),
                                    "StreetLines2": "{}".format(
                                        delivery_partner_id.street2 or "N/A"
                                    ),
                                    "City": "{}".format(delivery_partner_id.city.upper()),
                                    "PostalCode": delivery_partner_id.zip,
                                    "CountryCode": "{}".format(
                                        delivery_partner_id.country_id.code
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

                if r.json()["ShipmentResponse"]:
                    response = r.json()["ShipmentResponse"]
                    if ("ShipmentIdentificationNumber" not in response) or ("DispatchConfirmationNumber" not in response):
                        raise UserError(
                            "Error: {}".format(response["Notification"][0]["Message"])
                        )
                    self.carrier_tracking_ref = response["ShipmentIdentificationNumber"]
                    self.carrier_dispatch_ref = response["DispatchConfirmationNumber"]

                    if response["LabelImage"]:
                        self.env["ir.attachment"].create(
                            {
                                "name": "Label: {}".format(self.name),
                                "type": "binary",
                                "datas": response["LabelImage"][0]["GraphicImage"],
                                "datas_fname": "Label"
                                + self.name
                                + ".{}".format(
                                    response["LabelImage"][0]["LabelImageFormat"]
                                ),
                                "store_fname": self.name,
                                "res_model": self._name,
                                "res_id": self.id,
                                "mimetype": "application/x-pdf",
                            }
                        )
                        # rma
                        rma_id.delivery_tag = response["LabelImage"][0]["GraphicImage"]
                    if response["PackagesResult"]:
                        shipment_reference = ""
                        for package in response["PackagesResult"]["PackageResult"]:
                            shipment_reference += "{} ".format(
                                package["TrackingNumber"]
                            )
                        self.write({"shipment_reference": shipment_reference})
            except requests.exceptions.RequestException as e:
                raise UserError("Error: {}".format(e))

        else:
            return super(StockBatchPicking, self).send_shipping()
