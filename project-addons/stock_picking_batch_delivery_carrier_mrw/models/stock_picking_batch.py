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
from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken
from zeep.plugins import HistoryPlugin
from lxml import etree
import base64
import urllib
import ssl
from requests import Session
from requests.auth import HTTPBasicAuth

from odoo.exceptions import ValidationError, UserError, AccessError

from datetime import datetime, timedelta
import pytz

import logging.config

class StockBatchPicking(models.Model):

    _inherit = 'stock.picking.batch'

    mrw_franchise_delivery = fields.Selection([
        ('N', 'No'),
        #('R', 'Pick up on franchise'),
        ('E', 'Delivery on franchise'),
        #('A', 'Pick up and delivery on franchise')
    ], default='N')

    mrw_service = fields.Selection([
        ('0000', 'Urgente 10'),
        ('0005', 'Urgente Hoy'),
        ('0010', 'Promociones'),
        ('0100', 'Urgente 12'),
        ('0110', 'Urgente 14'),
        ('0120', 'Urgente 22'),
        ('0200', 'Urgente 19'),
        ('0205', 'Urgente 19 Expedición'),
        ('0210', 'Urgente 19 Más 40 Kilos'),
        ('0220', 'Urgente 19 Portugal'),
        ('0230', 'Bag 19'),
        ('0235', 'Bag 14'),
        ('0300', 'Económico'),
        ('0310', 'Económico Más de 40 Kilos'),
        ('0350', 'Económico Interinsular'),
        ('0400', 'Express Documentos'),
        ('0450', 'Express 2 Kilos'),
        ('0480', 'Caja Express 3 Kilos'),
        ('0490', 'Documentos 14'),
        ('0800', 'Ecommerce'),
        ('0810', 'Ecommerce Canje')
    ])

    mrw_frequency = fields.Selection([
        ('1', 'Frequency 1'),
        ('2', 'Frequency 2')
    ])

    mrw_saturday_delivery = fields.Selection([
        ('S', 'Yes'),
        ('N', 'No')
    ], default='N')

    mrw_830_delivery = fields.Selection([
        ('S', 'Yes'),
        ('N', 'No')
    ], default='N')

    mrw_delivery_hangle = fields.Selection([
        ('N', 'No handle'),
        ('O', 'Origin'),
        ('D', 'Destination')
    ], default='N')

    mrw_delivery_return = fields.Selection([
        ('N', 'No Return'),
        ('O', 'Picking return, payment on origin'),
        ('D', 'Picking return, payment on destination'),
        ('S', 'Goods return')
    ], default='N')

    mrw_instant_notice = fields.Selection([
        ('N', 'No'),
        ('R', 'Instant notice on picking'),
        ('E', 'Instante notice on delivery'),
    ], default='N')

    mrw_delivery_refund = fields.Selection([
        ('N', 'No refundable'),
        ('O', 'Comission in origin'),
        ('D', 'Comission in destination')
    ], default='N')

    mrw_refund_quantity = fields.Float('Refund amount')

    mrw_goods_type = fields.Selection([
        ('DOC', 'Documents'),
        ('MCV', 'Samples with commercial value'),
        ('MSV', 'Samples with no commercial value'),
        ('ATV', 'High value'),
        ('BTV', 'Low value')
    ], string='Customs Duty')

    mrw_declared_value = fields.Float('Declared value', help="Declared value for customs duty")

    mrw_mail_notification = fields.Boolean('Notify client by mail')
    mrw_phone_notification = fields.Boolean('Notify client by phone')

    mrw_notice_type = fields.Selection([
        ('1', 'Delivery'),
        ('2', 'Tracking'),
        ('3', 'Delivery on franchise'),
        ('4', 'Alert before delivery'),
        ('5', 'Alert after origin pick up')
    ])

    mrw_delivery_insurance = fields.Selection([
        ('1', 'General Goods'),
        ('2', 'Jewelry and valuable items'),
        ('3', 'Living animals')
    ])

    mrw_insurance_value = fields.Float('Insuranced value')


    @api.multi
    def write(self, vals):
        res = super().write(vals)
        if self.carrier_id.code == 'MRW':
            if vals.get('carrier_id', False):
                self.onchange_carrier_id()
            return res

    @api.onchange('carrier_id')
    def onchange_carrier_id(self):
        if self.carrier_id.code == 'MRW':
            pickings_total_value = 0.0
            for pick in self.picking_ids:
                pickings_total_value += pick.amount_total
            self.mrw_refund_quantity = pickings_total_value
            self.mrw_declared_value = pickings_total_value
            self.mrw_insurance_value = pickings_total_value
            
    def create_client(self):
        session = Session()
        session.verify = False       

        try:
            transport = Transport(cache=SqliteCache(), session=session)
            history = HistoryPlugin()
            if self.carrier_id.account_id.test_enviroment:
                url = self.env['ir.config_parameter'].get_param("stock_picking_batch_delivery_carrier_mrw.sagec_test_url")
            else:
                url = self.env['ir.config_parameter'].get_param("stock_picking_batch_delivery_carrier_mrw.sagec_url")
            client = Client(url, transport=transport, plugins=[history])

            if client:
                print("client: {}".format(client))
                return client, history
            else:
                raise AccessError(_("Not possible to establish a client."))
        except Exception as e:
            raise AccessError(_("Access error message: {}".format(e)))

    def setMRWHeaders(self, client):

        try:
            element_type = client.get_element("{http://www.mrw.es/}AuthInfo")
            headers = element_type(
                CodigoFranquicia=self.carrier_id.account_id.mrw_franchise,
                CodigoAbonado=self.carrier_id.account_id.mrw_account,
                CodigoDepartamento='',
                UserName=self.carrier_id.account_id.account,
                Password=self.carrier_id.account_id.password
            )
            return headers
        except Exception as e:
            print("Error: {}".format(e))
            return False
    
    def get_carrier_label(self, client, headers, numeroEnvio):
        EtiquetaEnvio = {
            'request': {
                'NumeroEnvio': numeroEnvio,
                'SeparadorNumerosEnvio': '',
                'ReportTopMargin': 1100,
                'ReportLeftMargin': 650
            }
        }

        label = client.service.EtiquetaEnvio(**EtiquetaEnvio, _soapheaders=[headers])
        return label
                    

    def send_shipping(self):
        if self.carrier_id.code == 'MRW':

            if not self.carrier_id.account_id:
                raise UserError("Delivery carrier has no account.")

            client, history = self.create_client()

            if client:

                try:
                
                    headers = self.setMRWHeaders(client)

                    requestedPackages = []
                    cur_pack = 1
                    while cur_pack <= self.carrier_packages:
                        package_info = {
                            'BultoRequest': {
                                'Alto': self.height,
                                'Largo': self.length,
                                'Ancho': self.width,
                                'Peso': self.carrier_weight/self.carrier_packages,
                                'NumeroBulto': "{}".format(cur_pack)
                            }
                        }
                        requestedPackages.append(package_info)
                        cur_pack+=1

                    notices = []
                    if self.mrw_phone_notification:
                        phone_notification = {
                            'NotificacionRequest': {
                                'CanalNotificacion': '2',
                                'TipoNotificacion': self.mrw_notice_type,
                                'MailSMS': self.partner_id.phone or self.partner_id.mobile
                            }
                        }
                        notices.append(phone_notification)

                    if self.mrw_mail_notification:
                        mail_notification = {
                            'NotificacionRequest': {
                                'CanalNotificacion': '1',
                                'TipoNotificacion': self.mrw_notice_type,
                                'MailSMS': self.partner_id.email
                            }
                        }
                        notices.append(mail_notification)

                    TransmEnvio = {
                        'request': {
                            'DatosEntrega': {
                                'Direccion': {
                                    'Via': "{} {}".format(self.partner_id.street or "", self.partner_id.street2 or ""),
                                    'CodigoPostal': self.partner_id.zip,
                                    'Poblacion': self.partner_id.city,
                                    'Provincia': self.partner_id.state_id.name
                                },
                                'Nif': self.partner_id.vat,
                                'Nombre': self.partner_id.name,
                                'Telefono': self.partner_id.phone or self.partner_id.phone or ''
                            },
                            'DatosServicio': {
                                'Fecha': datetime.now().strftime("%d/%m/%Y"), #self.date.strftime("%d/%m/%Y"),
                                'Referencia': self.name,
                                'CodigoServicio': self.mrw_service,
                                'Frecuencia': self.mrw_frequency if self.mrw_service == '0005' else '',
                                #'Bultos': requestedPackages,
                                'NumeroBultos': self.carrier_packages,
                                'Peso': round(self.carrier_weight),
                                'EntregaSabado': self.mrw_saturday_delivery,
                                'Entrega830': self.mrw_830_delivery,
                                'EntregaPartirDe': '',
                                'Gestion': self.mrw_delivery_hangle,
                                'Retorno': self.mrw_delivery_return,
                                'ConfirmacionInmediata': self.mrw_instant_notice,
                                'Reembolso': self.mrw_delivery_return,
                                'ImporteReembolso': self.mrw_refund_quantity if self.mrw_delivery_return != 'N' else '',
                                'TipoMercancia': self.mrw_goods_type,
                                'ValorDeclarado': self.mrw_declared_value if self.mrw_goods_type else '',
                                'Notificaciones': notices,
                                'SeguroOpcional': {
                                    'CodigoNaturaleza': self.mrw_delivery_insurance if self.mrw_delivery_insurance else '',
                                    'ValorAsegurado': self.mrw_insurance_value if self.mrw_delivery_insurance else ''
                                }
                            }
                        }
                    }

                    res = client.service.TransmEnvio(**TransmEnvio, _soapheaders=[headers])
                except Exception as e:
                    raise AccessError(_("Access error message: {}".format(e)))

                if res['Estado'] == '0':
                    raise AccessError(_("Error message: {}".format(res['Mensaje'])))
                elif res['Estado'] == '1':
                    
                    self.write({
                        'delivery_status': 'R',
                        'tracking_code': res['NumeroEnvio'],
                        'shipment_reference': res['NumeroSolicitud']
                    })                 
                    
                    try:                
                        label = self.get_carrier_label(client, headers, res['NumeroEnvio'])
                    except Exception as e:
                        _logger.error(_('Connection error: {}, while trying to retrieve the label.'.format(e)))
                        return
                    
                    if label['Estado'] == '1':
                        file_b64 = base64.b64encode(label['EtiquetaFile'])
                        attatchment = self.env['ir.attachment'].create({
                            'name': "Label: {}".format(self.name),
                            'type': 'binary',
                            'datas': file_b64,
                            'datas_fname': 'Label' + self.name + '.pdf',
                            'store_fname': self.name,
                            'res_model': self._name,
                            'res_id': self.id,
                            'mimetype': 'application/x-pdf'
                        })
                    elif label['Estado'] == '0':
                        raise AccessError(_("Error while trying to retrieve the label: {}".format(label['Mensaje'])))
                    else:
                        raise AccessError(_("Error while trying to retrieve the label"))
                else:
                    raise AccessError(_("Unknown error with the SOAP connection."))

            else:
                raise AccessError(_("Not possible to establish a client."))

        res = super(StockBatchPicking, self).send_shipping()