from odoo import api, models, fields, exceptions, _
import logging
from odoo.tests.common import Form
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.multi
    @api.depends("purchase_regularice_invoice_id", "state")
    def _get_regularize(self):
        no_reg = self.filtered(lambda x: x.state in ['draft', 'cancel'] or x.type in ['in_refund', 'in_invoice'] or not x.team_id.invoice_on_company)
        no_reg.write({'regularize': 'no'})
        # no.invoice_line_ids.write({'regularize': 'no'})
        to_invoice = self - no_reg
        for invoice in to_invoice:
            if invoice.purchase_regularice_invoice_id:
                invoice.regularize = "invoiced"
            else:
                invoice.regularize = 'to_invoice'
            # invoice.invoice_line_ids.write({'regularize': 'to_invoice'})

    regularize = fields.Selection(
        [("no", "No"), ("to_invoice", "To invoice"), ("invoiced", "Invoiced")],
        compute="_get_regularize",
        store=True,)
    purchase_regularice_invoice_id = fields.Many2one("account.invoice", "Regularice Invoice")
    ic_sale_id = fields.Many2one('sale.order', 'Sale')

    def invoice_validate(self):
        res = super().invoice_validate()
        for invoice in self:
            if invoice.type == 'out_invoice' and invoice.auto_invoice_id and \
                    invoice.sudo().auto_invoice_id.reference == "TEMP":
                invoice.sudo().auto_invoice_id.reference = invoice.invoice_number

        return res
  
    @api.multi
    def _inter_company_create_invoice(self, dest_company):
        inter_invoice = self.search([
            ('auto_invoice_id', '=', self.id),
            ('company_id', '=', dest_company.id)
        ])
        force_number = False
        if inter_invoice and inter_invoice.state in ['draft', 'cancel']:
            force_number = inter_invoice.number
        if force_number:
            res = super(AccountInvoice,
                         self.with_context(force_number=force_number)).\
                _inter_company_create_invoice(dest_company)
        else:
            res = super()._inter_company_create_invoice(dest_company)
        
        if res['dest_invoice']:
            dest_invoice = res['dest_invoice']
            dest_invoice.message_post(body='Factura Intercompañia: Desde <a href="#" '
                        'data-oe-model="account.invoice" '
                        'data-oe-id="%d">%s</a> <hr/>'%(self.id, dest_invoice.reference))

        return res


    @api.multi
    def _prepare_invoice_data(self, dest_company):
        vals = super()._prepare_invoice_data(dest_company)
        ## vals['sale_type_id'] = self._get_ic_type_id(dest_company).id

        if self.env.context.get('force_number', False):
            vals['invoice_number'] = self.env.context['force_number']
            vals['number'] = self.env.context['force_number']
        return vals


    @api.model
    def create(self, vals):
        invoice_id = super().create(vals)
        return invoice_id

class AccountInvoiceLine(models.Model):

    _inherit = "account.invoice.line"

    regularice_line_ids = fields.One2many("account.invoice.line",
                                          "regularice_invoice_line_id",
                                          "Regularice lines")
    regularize = fields.Selection([("no", "No"), ("to_invoice", "To invoice"), ("invoiced", "Invoiced")])
    regularice_invoice_line_id = fields.Many2one("account.invoice.line", "Invoice line", readonly=True)

    @api.model
    def _prepare_invoice_line_data(self, dest_invoice, dest_company):
        return super()._prepare_invoice_line_data(dest_invoice, dest_company)

    def get_ic_line_sign(self):
        # devuelvo +1 en out
        # devuelvo -1 en in_refund
        return +1
        if self.location_dest_id.usage == 'customer' and self.location_id.usage in ['internal', 'view']:
            return 1
        if self.location_id.usage == 'customer' and self.location_dest_id.usage in ['internal', 'view']:
            return -1

    