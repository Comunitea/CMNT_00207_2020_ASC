##############################################################################
#
#    Author: Santi Argüeso
#    Copyright 2014 Pexego Sistemas Informáticos S.L.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    deposit = fields.Boolean('Deposit')
    deposit_date = fields.Date('Date Dep.')

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'deposit')
    def _compute_amount(self):
        super(SaleOrderLine, self.filtered(lambda x: not x.deposit))._compute_amount()
        for line in self.filtered('deposit'):
            line.update({
                'price_subtotal': 0.0})

    @api.onchange('deposit')
    def onchange_deposit(self):
        if self.deposit:
            current_date = datetime.utcnow()
            delta = timedelta(days=self.order_id.partner_id.property_deposit_days)
            result = current_date + delta
            self.deposit_date = result.strftime(DEFAULT_SERVER_DATE_FORMAT)
        else:
            self.deposit_date = False

    @api.multi
    def invoice_line_create_vals(self, invoice_id, qty):
        lines = self.env['sale.order.line']
        for line in self:
            if not line.deposit or self.env.context.get('invoice_deposit', False):
                lines += line
        return super(SaleOrderLine, lines).invoice_line_create_vals(invoice_id, qty)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    deposit_ids = fields.One2many('stock.deposit', 'sale_id', 'Deposits')
    deposit_count = fields.Integer('deposit count', compute='_get_deposit_len', store=True)

    @api.multi
    @api.depends('deposit_ids')
    def _get_deposit_len(self):
        for sale in self:
            sale.deposit_count = len(sale.deposit_ids)

    @api.multi
    def action_confirm(self):

        res = super().action_confirm()
        for line in self.order_line:
            if line.deposit:
                #line.qty_invoiced = line.product_uom_qty
                line.invoice_status = 'invoiced'
        return res

    def _finalize_invoices(self, invoices, references):

        if self._context.get('invoice_deposit'):
            for invoice in references.keys():
                sale_id = references[invoice]
                if sale_id.deposit_count:
                    sequence = max(line.sequence for line in invoice.invoice_line_ids)
                    for line in sale_id.order_line.filtered('deposit'):
                        sequence += 1
                        #sale_line_id = line.move_id.sale_line_id
                        line_vals_list = line.invoice_line_create_vals(invoice.id, line.qty_to_invoice)
                        line_vals_list[0]['sequence'] = sequence
                        self.env['account.invoice.line'].create(line_vals_list)
        return super()._finalize_invoices(invoices=invoices, references=references)