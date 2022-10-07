from odoo import models, exceptions, _, fields
from odoo.tests.common import Form
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging

_logger = logging.getLogger(__name__)

class WzdIntercompanyRegularization(models.TransientModel):

    _name = "wzd.intercompany.regularization"

    date_from = fields.Date("From date")
    date_to = fields.Date("To date")

    def get_ic_journal(self, company, team_id):
        if team_id.purchase_ic_journal_id and team_id.purchase_ic_journal_id.sudo().company_id == company:
            return team_id.purchase_ic_journal_id            
        return self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)

    def action_regularize(self):
        domain = [('regularize', '=', 'to_invoice')]
        if self.date_from:
            domain += [('date_invoice', '>=', self.date_from)]
        if self.date_to:
            domain += [('date_invoice', '<=', self.date_to)]

        to_regularize = self.env['account.invoice'].search(domain)

        _logger.info(">>> %d facturas a regularizar" % len(to_regularize))

        invoices = self.env['account.invoice']
        # company_ids = to_regularize.mapped('team_id.invoice_on_company')
        partner_ids = to_regularize.sudo().mapped('ic_sale_id.company_id.partner_id')
        team_ids = to_regularize.mapped('team_id')
        company = self.env.user.company_id
        for team_id in team_ids:
            purchase_journal = self.get_ic_journal(company, team_id)
            for partner in partner_ids:
                
                _logger.info(">>> Facturas de %s y %s"%(company.name, partner.name))
                invoices_to_reg = to_regularize.filtered(lambda x: x.ic_sale_id.sudo().company_id.partner_id == partner and x.team_id == team_id)
                if not invoices_to_reg:
                    continue
                partner_id_company = invoices_to_reg[0].ic_sale_id.sudo().company_id
                dest_invoice_data = Form(self.env['account.invoice'].with_context(default_type='in_invoice'))
                dest_invoice_data.partner_id = partner
                dest_invoice_data.date_invoice = fields.Date.today()
                dest_invoice_data.reference = "TEMP"
                dest_invoice_data.origin = ','.join(to_regularize.mapped('number'))
                dest_invoice_data.journal_id = purchase_journal
                dest_invoice_data.currency_id = company.currency_id
                #dest_invoice_data.team_id = team_id
                # dest_invoice_data.sale_type_id = self.env.user.company_id.sale_order_type_intercompany
                invoice = dest_invoice_data.save()
                # No tiene sentido pasar el team_id
                invoice.team_id = team_id
                invoices |= invoice
                product_ids = {}
                body = "Esta factura se ha creado a partir de las siguientes facturas: <ul>"
                for inv in invoices_to_reg:
                    inv.purchase_regularice_invoice_id = invoice.id
                    body += '<li> <a href="#" data-oe-model="account.invoice" data-oe-id="%d">%s</a> </li>'%(inv.id, inv.reference)
                body += "</ul>"
                invoice.message_post(body=body)
                # Salidas de los movimientos de la compañia
                for line in invoices_to_reg.mapped("invoice_line_ids"):
                    price_subtotal = line.price_subtotal
                    quantity = line.quantity
                    if line.product_id.id not in product_ids:
                        product_ids[line.product_id.id] = [quantity, [line.id], price_subtotal]
                    else:
                        product_ids[line.product_id.id][0] += quantity
                        product_ids[line.product_id.id][1].append(line.id)
                        product_ids[line.product_id.id][2] += price_subtotal
        
                all_line_vals = []
                for product_id in product_ids:
                    quantity = product_ids[product_id][0]
                    price_subtotal = product_ids[product_id][2]
                    price_unit = price_subtotal / (quantity or 1.0)
                    product = self.env['product.product'].browse(product_id)
                    account_id = product.property_account_expense_id.id or product.categ_id.property_account_expense_categ_id.id
                    _logger.info("Linea para %s"%product.display_name)
                    line_vals = {'product_id': product_id,
                                'quantity': quantity,
                                'price_unit': price_unit,
                                # 'discount': pricelist_item_id.percent_price,
                                'name': product.display_name,
                                'account_id': account_id,
                                'uom_id': product.uom_id.id,
                                'invoice_line_tax_ids': [(6, 0, product.supplier_taxes_id.ids)],
                                'invoice_id': invoice.id,
                                # 'regularice_line_ids': [(6, 0, product_ids[product_id][1])]
                                }
                    new_line = self.env['account.invoice.line'].create(line_vals)
                    new_line._onchange_product_id()
                    self._update_wzd_price_list(new_line, from_company=partner_id_company)
                    all_line_vals.append(line_vals)
                # new_line = self.env['account.invoice.line'].create(all_line_vals)
                invoice.compute_taxes()


        # Devuelvo listado de facturas
        action = self.env.ref('account.action_vendor_bill_template').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.invoice_supplier_form').id,
                          'form')]
            if 'views' in action:
                action['views'] = form_view + \
                    [(state, view) for state, view in action['views']
                     if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.ids[0]
        return action


    def _update_wzd_price_list(self, line, from_company):
        #Pasamos como partner:
        partner_id = line.invoice_id.partner_id
        
        product = line.product_id.with_context(
            lang=partner_id.lang,
            partner=partner_id.id,
            quantity=line.quantity,
            date=line.invoice_id.date_invoice,
            pricelist=partner_id.property_product_pricelist.id,
            uom=line.uom_id.id,
            fiscal_position=(
                partner_id.property_account_position_id.id)
        )
        seller = product._select_seller(partner_id=partner_id, quantity=line.quantity, date=line.invoice_id.date_invoice, uom_id=line.uom_id, params=False)
        if not seller:
            ## if line.product_id.seller_ids.filtered(lambda s: s.name.id == line.partner_id.id):
            line.price_unit = 0.0
            return

        line.price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, product.supplier_taxes_id, line.invoice_line_tax_ids, line.invoice_id.company_id) if seller else 0.0
        