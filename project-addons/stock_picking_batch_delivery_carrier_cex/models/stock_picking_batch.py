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

import json
import os
import re
from base64 import b64decode, b64encode
from datetime import date
from xml.dom.minidom import parseString

import requests

from odoo import _, models
from odoo.exceptions import UserError
from unidecode import unidecode

try:
    import genshi
    import genshi.template
except (ImportError, IOError) as err:
    import logging

    logging.getLogger(__name__).warn("Module genshi is not available")

loader = genshi.template.TemplateLoader(
    os.path.join(os.path.dirname(__file__), "template"), auto_reload=True
)


class StockBatchPicking(models.Model):

    _inherit = "stock.picking.batch"

    def send_shipping(self):
        super(StockBatchPicking, self).send_shipping()
        if self.carrier_id.code == "CEX":

            if not self.carrier_id.account_id:
                raise UserError("Delivery carrier has no account.")

            if self.carrier_id.account_id.test_enviroment:
                url = "{}apiRestGrabacionEnvio/json/grabacionEnvio".format(
                    self.carrier_id.account_id.service_test_url
                )
            else:
                url = "{}apiRestGrabacionEnvio/json/grabacionEnvio".format(
                    self.carrier_id.account_id.service_url
                )

            username = self.carrier_id.account_id.account
            password = self.carrier_id.account_id.password
            data = self._get_cex_label_data()
            try:
                response = requests.post(
                    url, auth=(username, password), json=data, timeout=5
                )
                rjson = json.loads(re.search("({.*})", response.text).group(1))
            except requests.exceptions.Timeout:
                rjson = {
                    "codigoRetorno": 999,
                    "mensajeRetorno": "\n\nEl servidor está tardando mucho en responder.",
                }
            except Exception:
                rjson = {
                    "codigoRetorno": 999,
                    "mensajeRetorno": "\n\n" + response.text,
                }
            retorno = rjson["codigoRetorno"]
            message = rjson["mensajeRetorno"]

            if retorno == 0:
                self.carrier_tracking_ref = rjson["datosResultado"]
                if self.carrier_id.account_id.file_format == "PDF":
                    for label_result in rjson["etiqueta"]:
                        self.env["ir.attachment"].create(
                            {
                                "name": self.name
                                + "_"
                                + self.carrier_tracking_ref
                                + ".pdf",
                                "type": "binary",
                                "datas": b64decode(label_result["etiqueta1"]),
                                "datas_fname": self.name
                                + "_"
                                + self.carrier_tracking_ref
                                + ".pdf",
                                "store_fname": self.name,
                                "res_model": self._name,
                                "res_id": self.id,
                                "mimetype": "application/x-pdf",
                            }
                        )
                else:
                    self.cex_result = rjson["etiqueta"][0]["etiqueta2"]
                    for label_result in rjson["etiqueta"]:
                        self.env["ir.attachment"].create(
                            {
                                "name": self.name
                                + "_"
                                + self.carrier_tracking_ref
                                + ".pdf",
                                "type": "binary",
                                "datas": b64encode(
                                    label_result["etiqueta2"].encode("utf-8")
                                ),
                                "datas_fname": self.name
                                + "_"
                                + self.carrier_tracking_ref
                                + ".pdf",
                                "store_fname": self.name,
                                "res_model": self._name,
                                "res_id": self.id,
                                "mimetype": "text/plain",
                            }
                        )
                self.print_created_labels()
            else:
                raise UserError(
                    _("CEX Error: %s %s")
                    % (retorno or 999, message or "Webservice ERROR.")
                )

    def _get_cex_label_data(self):
        self.ensure_one()

        partner = self.partner_id
        number_of_packages = self.carrier_packages or 1
        phone = partner.mobile or partner.phone or ""
        listaBultos = []
        for i in range(0, number_of_packages):
            listaBultos.append(
                {
                    "ancho": "",
                    "observaciones": "",
                    "kilos": "",
                    "codBultoCli": "",
                    "codUnico": "",
                    "descripcion": "",
                    "alto": "",
                    "orden": i + 1,
                    "referencia": "",
                    "volumen": "",
                    "largo": "",
                }
            )

        streets = []
        if partner.street:
            streets.append(unidecode(partner.street))
        if partner.street2:
            streets.append(unidecode(partner.street2))
        if (
            not streets
            or not partner.city
            or not partner.zip
            or not partner.zip
        ):
            raise UserError("Review partner data")
        if self.carrier_id.account_id.file_format not in ("PDF", "ZPL"):
            raise UserError("Format file not supported by cex")
        if not self.carrier_id.service_code:
            raise UserError("Set service to the picking")
        if not self.carrier_weight or self.carrier_weight == 0.0:
            raise UserError("Set weight to the picking")
        data = {
            "solicitante": self.carrier_id.account_id.cex_solicitante,
            "canalEntrada": "",
            "numEnvio": "",
            "ref": self.name[:20],
            "refCliente": "",
            "fecha": date.today().strftime("%d%m%Y"),
            "codRte": self.carrier_id.account_id.cex_codRte,
            "nomRte": self.env.user.company_id.name,
            "nifRte": "",
            "dirRte": self.env.user.company_id.street,
            "pobRte": self.env.user.company_id.city,
            "codPosNacRte": self.env.user.company_id.zip,
            "paisISORte": "",
            "codPosIntRte": "",
            "contacRte": self.env.user.company_id.name,
            "telefRte": self.env.user.company_id.phone,
            "emailRte": self.env.user.company_id.email,
            "codDest": "",
            "nomDest": partner.name[:40] or "",
            "nifDest": "",
            "dirDest": "".join(streets)[:300],
            "pobDest": partner.city[:50] or "",
            "codPosNacDest": partner.zip,
            "paisISODest": "",
            "codPosIntDest": "",
            "contacDest": partner.name[:40] or "",
            "telefDest": phone[:15],
            "emailDest": partner.email and partner.email[:75] or "",
            "contacOtrs": "",
            "telefOtrs": "",
            "emailOtrs": "",
            "observac": self.delivery_note or "",
            "numBultos": number_of_packages or 1,
            "kilos": "%.3f" % (self.carrier_weight or 1),
            "volumen": "",
            "alto": "",
            "largo": "",
            "ancho": "",
            "producto": self.carrier_id.service_code.carrier_code,
            "portes": "P",
            "reembolso": "",  # TODO cash_on_delivery
            "entrSabado": "",
            "seguro": "",
            "numEnvioVuelta": "",
            "listaBultos": listaBultos,
            "codDirecDestino": "",
            "password": "string",
            "listaInformacionAdicional": [
                {
                    "tipoEtiqueta": self.carrier_id.account_id.file_format
                    == "PDF"
                    and "1"
                    or "2",
                    "etiquetaPDF": "",
                }
            ],
        }
        return data


class StockPicking(models.Model):

    _inherit = "stock.picking"

    def check_shipment_status(self):
        if self.carrier_id.carrier_type == "cex":
            if self.carrier_id.account_id.test_enviroment:
                url = "{}apiRestSeguimientoEnvios/rest/seguimientoEnvios".format(
                    self.carrier_id.account_id.service_test_url
                )
            else:
                url = "{}apiRestSeguimientoEnvios/rest/seguimientoEnvios".format(
                    self.carrier_id.account_id.service_url
                )
            username = self.carrier_id.account_id.account
            password = self.carrier_id.account_id.password
            vals = {
                "solicitante": self.carrier_id.account_id.cex_solicitante,
                "dato": self.carrier_tracking_ref,
            }
            tmpl = loader.load("check_status.xml")
            xml = tmpl.generate(**vals).render()
            try:
                response = requests.post(
                    url,
                    auth=(username, password),
                    data=xml,
                    timeout=5000,
                    headers={"Content-Type": "text/xml; charset=utf-8"},
                )
                xml_start = response.content.decode().find("<")
                result_xml = parseString(response.content.decode()[xml_start:])
                state_nodes = result_xml.getElementsByTagName("EstadoEnvios")
                for state_node in state_nodes:
                    if (
                        state_node.getElementsByTagName("CodEstado")
                        and state_node.getElementsByTagName("CodEstado")[
                            0
                        ].firstChild.data
                        == "12"
                    ):
                        self.delivered = True
                        break
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
            ):
                rjson = {
                    "codigoRetorno": 999,
                    "mensajeRetorno": "\n\nEl servidor está tardando mucho en responder.",
                }
            except:
                rjson = {
                    "codigoRetorno": 999,
                    "mensajeRetorno": "\n\n" + response.text,
                }

        return super(StockPicking, self).check_shipment_status()
