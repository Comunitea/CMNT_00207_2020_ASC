# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from datetime import datetime
from dateutil import relativedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class StockRule(models.Model):
    _inherit = 'stock.rule'


    def _make_po_select_supplier(self, values, suppliers):
        """ Method intended to be overridden by customized modules to implement any logic in the
            selection of supplier.
        """
        ### SI viene forzado, devulevo lo que corresponda. No lo uso pero ....
        if values.get('po_supplier', False):
            return values['po_supplier']

        po_supplier = super()._make_po_select_supplier(values, suppliers)
        ### Si hay más de 2 suppliers y si viene de primara vez con make_2_po:
        if values.get('make_2_po', False) and len(suppliers) > 1:
            ## consigo el 2º supplier
            product_id = values['product_id']
            days_to_second_orderpoint = product_id.replenish_type and product_id.replenish_type.days_to_second_orderpoint or 3
            if po_supplier.delay > days_to_second_orderpoint:
                supplier_2 = suppliers[1] if suppliers[0] == po_supplier else suppliers[0]
                op_id = values['orderpoint_id'] 
                days = op_id.lead_days or 0.0
                days += supplier_2.delay or 0.0
                date_planned = datetime.today() + relativedelta(days=days)
                values.update(make_2_po=False, po_supplier=supplier_2, date_planned=date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
                self._run_buy(values['product_id'], values['product_qty'], values['product_uom'], values['location_id'], values['name'], values['origin'], values)
        return po_supplier

    @api.multi
    def _run_buy(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        res = super(StockRule, self)._run_buy(
            product_id, product_qty, product_uom, location_id, name,
            origin, values)
        
        ## Compruebo si el producto tiene 2º pedido de compra y no viene ya desde una segund compra (po_suplier en values)

        if not values.get('po_supplier', False) and (not product_id.replenish_type or product_id.replenish_type.days_to_second_orderpoint > 1):
            quantity_per_cent = product_id.replenish_type and product_id.replenish_type.quantity_per_cent or 50
            values.update({
                'product_id' : product_id,
                'product_qty': int(product_qty * quantity_per_cent/100),
                'location_id': location_id,
                'product_uom': product_uom,
                'name': name, 
                'origin': origin,
                'make_2_po': True
            })
            suppliers = product_id.seller_ids\
                .filtered(lambda r: (not r.company_id or r.company_id == values['company_id']) and (not r.product_id or r.product_id == product_id) and r.name.active)

            self._make_po_select_supplier(values, suppliers)
        
        return res
