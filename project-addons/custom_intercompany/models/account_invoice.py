from odoo import api, models, fields, exceptions, _
import logging
from odoo.tests.common import Form
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.multi
    @api.depends("state", "type", "purchase_regularice_invoice_id")
    def _get_regularize(self):
        for invoice in self:
            if invoice.state in ['draft', 'cancel'] or invoice.type in ['in_refund', 'in_invoice'] or not invoice.team_id.invoice_on_company:
                invoice.regularize = False
            else:
                if invoice.purchase_regularice_invoice_id:
                    invoice.regularize = "invoiced"
                else:
                    invoice.regularize = 'to_invoice'
        
    regularize = fields.Selection(
        [("no", "No"), ("to_invoice", "To invoice"), ("invoiced", "Invoiced")],
        #default='no')
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
        res = super()._inter_company_create_invoice(dest_company=dest_company)
        if res['dest_invoice']:
            dest_invoice = res['dest_invoice']
            dest_invoice.message_post(body='Factura Intercompañia: Desde <a href="#" '
                        'data-oe-model="account.invoice" '
                        'data-oe-id="%d">%s</a> <hr/>'%(self.id, dest_invoice.reference))

        return res

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
        """ Valores intercompañia
        """
        vals = super()._prepare_invoice_data(dest_company)
        if self.team_id and self.team_id.ic_journal_id and vals['journal_id'] != self.team_id.ic_journal_id.id:
                journal_id = self.team_id.ic_journal_id
                vals['journal_id'] = self.team_id.ic_journal_id.id
                if journal_id.currency_id and vals['currency_id'] != journal_id.currency_id.id:
                    vals['currency_id'] = journal_id.currency_id.id
        ## vals['sale_type_id'] = self._get_ic_type_id(dest_company).id
        if self.env.context.get('force_number', False):
            vals['invoice_number'] = self.env.context['force_number']
            vals['number'] = self.env.context['force_number']
        return vals


class AccountInvoiceLine(models.Model):

    _inherit = "account.invoice.line"

    # regularice_line_ids = fields.One2many("account.invoice.line",
    #                                       "regularice_invoice_line_id",
    #                                        "Regularice lines")
    # regularice_invoice_line_id = fields.Many2one("account.invoice.line", "Invoice line", readonly=True)

    # @api.model
    # def _prepare_invoice_line_data(self, dest_invoice, dest_company):
    #     return super()._prepare_invoice_line_data(dest_invoice, dest_company)
