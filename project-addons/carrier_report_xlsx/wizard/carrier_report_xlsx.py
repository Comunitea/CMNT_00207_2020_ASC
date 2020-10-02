# Copyright 2020 Comunitea
# @author KIko Sánchez <kiko@comunitea.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round
from io import BytesIO
from datetime import datetime, timedelta

import xlsxwriter
import logging
import base64

logger = logging.getLogger(__name__)



class ReportCarrierReportPDF(models.AbstractModel):
    _name = 'report.carrier_report_xlsx.report_deliveries'
    _description = "Carrier report PDF"

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data,
            'docs': docs,
        }

class CarrierreportXlsx(models.TransientModel):
    _name = 'carrier.report.xlsx'
    _description = 'Generate XLSX report for carrier deliveries'


    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Almacén')

    account_ids = fields.Many2many('carrier.account', string="Cuentas" )

    service_ids = fields.Many2many('delivery.carrier.service', string="Servivio")#, domain = [()])
    carrier_ids = fields.Many2many('delivery.carrier', string="Transportista")
    team_ids = fields.Many2many('crm.team', string="Equipo de ventas")
    stock_date_type = fields.Selection([
        ('present', 'Hoy'),
        ('past', 'Otro día'),
        ], string='Día', default='present')
    past_date = fields.Datetime(
        string='Día pasado',
        default=fields.Datetime.now)
    split_by_carrier = fields.Boolean(
        string='Mostrar transportista', default=True)
    split_by_service = fields.Boolean(
        string='Mostrar servicio', default=False)


    def _get_stock_picking_domain(self, date = fields.Date.today()):
        ## TODO revisar es to para incluir self.stock_date_type, self.past_date
        self.ensure_one()
        date_domain = [('date', '>=', fields.Date.to_string(date)), ('date', '<', fields.Date.to_string(date + timedelta(days=1)) )]
        domain = [('picking_type_id.code', '=', 'outgoing'), ('state', '=', 'done')]
        if self.warehouse_id:
            picking_type_ids = self.env['stock.picking.type'].search([('id', 'in', self.warehouse_id.ids)]).ids
            domain += [('picking_type_id', '=', picking_type_ids)]
        if self.account_ids:
            domain += [('carrier_id.account_id', 'in', self.account_ids.ids)]
        if self.service_ids:
             domain += [('service_code', '=', self.service_ids.ids)]
        if self.team_ids:
            domain += [('team_id', '=', self.team_ids.ids)]
        domain += date_domain
        return domain

    def _prepare_picking_fields(self):
        return ['name', 'partner_id', 'team_id', 'carrier_id', 'service_code', 'carrier_weight', 'carrier_packages', 'carrier_account_id', 'carrier_tracking_ref']

    def compute_picking_data(self, date=fields.Date.today()):
        spo = self.env['stock.picking.batch']
        picking_ids = spo.search(self._get_stock_picking_domain(date), order="carrier_id, service_code, name asc")#, self._prepare_picking_fields())
        return picking_ids


    def group_result(self, data):

        # 1ª agrupación
        # Por Delivery Carrier
        # Por Account (account_ids)
        # Por Servicio (service_ids)
        fields = ['carrier_account_id', 'carrier_id', 'service_code']
        result = {}
        for l in data:
            key_0 = l[fields[0]] and l[fields[0]]['name'] or 'Sin Agencia'
            if not key_0 in result.keys():
                name = l.carrier_account_id and l.carrier_account_id.name or 'Sin Agencia'
                key_0_dict = {'name': name,
                              'carrier_account_id': l.carrier_account_id,
                              'carrier_weight': l.carrier_weight,
                              'carrier_packages': l.carrier_packages,
                              'childs': {},
                              'contador': 1}
                result[key_0] = key_0_dict
            else:
                result[key_0]['carrier_weight'] += l.carrier_weight
                result[key_0]['carrier_packages'] += l.carrier_packages
                result[key_0]['contador'] += 1

            key_1 = l[fields[1]] and l[fields[1]]['name'] or 'Sin Transportista'
            if not key_1 in result[key_0]['childs'].keys():
                name =  l.carrier_id and l.carrier_id.name or 'Sin Transportista'
                key_1_dict = {'name': name,
                              'carrier_id': l.carrier_id,
                              'carrier_weight': l.carrier_weight,
                              'carrier_packages': l.carrier_packages,
                              'childs': {},
                              'contador': 1}
                result[key_0]['childs'][key_1] = key_1_dict
            else:
                result[key_0]['childs'][key_1]['carrier_weight'] += l.carrier_weight
                result[key_0]['childs'][key_1]['carrier_packages'] += l.carrier_packages
                result[key_0]['childs'][key_1]['contador'] += 1

            key_2 = l[fields[2]] and l[fields[2]]['name'] or 'Sin Servicio'
            if not key_2 in result[key_0]['childs'][key_1]['childs'].keys():
                name =  l.service_code and l.service_code.name or 'Sin Servicio'
                key_2_dict = {'name': name,
                              'service_code': l.service_code,
                              'carrier_weight': l.carrier_weight,
                              'carrier_packages': l.carrier_packages,
                              'contador': 1,
                              'batchs': []}
                result[key_0]['childs'][key_1]['childs'][key_2] = key_2_dict
            else:
                result[key_0]['childs'][key_1]['childs'][key_2]['carrier_weight'] += l.carrier_weight
                result[key_0]['childs'][key_1]['childs'][key_2]['carrier_packages'] += l.carrier_packages
                result[key_0]['childs'][key_1]['childs'][key_2]['contador'] += 1

            item = {'name': l.name[7:],
                    'partner': l.partner_id.name,
                    'team_id': l.team_id.name,
                    'carrier_tracking_ref': l.carrier_tracking_ref,
                    'carrier_packages': l.carrier_packages,
                    'carrier_weight': l.carrier_weight}
            result[key_0]['childs'][key_1]['childs'][key_2]['batchs'].append(item)

        return result


    def generate(self):

        self.ensure_one()
        logger.debug('Start generate XLSX carrier report valuation report')
        company = self.env.user.company_id
        company_id = company.id
        date = fields.Date.today()
        if self.stock_date_type != 'present':
            date = self.past_date
        batch_ids = self.compute_picking_data(date)
        if not batch_ids:
            raise UserError(_("No hay envíos."))

        data = {'res': self.group_result(batch_ids)}
        print(data)
        return self.env.ref('carrier_report_xlsx.action_report_deliveries').report_action(self, data=data)

