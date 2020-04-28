# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, _, exceptions


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.constrains('invoice_number')
    def check_last_invoice_number(self):
        for inv in self:
            if inv.invoice_number:
                sequence = inv.journal_id.invoice_sequence_id
                if inv.type in {'out_refund', 'in_refund'} and \
                        inv.journal_id.refund_inv_sequence_id:
                    sequence = inv.journal_id.refund_inv_sequence_id
                if sequence.implementation == 'no_gap':
                    prefix, suffix = sequence.\
                        with_context(ir_sequence_date=inv.date_invoice.
                                     strftime("%Y-%m-%d"),
                                     ir_sequence_date_range=inv.date_invoice.
                                     strftime("%Y-%m-%d")).\
                        _get_prefix_suffix()
                    num_char = inv.invoice_number.replace(prefix, '').\
                        replace(suffix, '')
                    padding = len(num_char)
                    num = int(num_char)
                    other_invoices = self.search([('invoice_number', '=like',
                                                   prefix + '%' + suffix),
                                                  ('date_invoice', '<=',
                                                   inv.date_invoice),
                                                  ('id', '!=', inv.id)],
                                                 limit=1)
                    if other_invoices:
                        num = num - sequence.number_increment
                        last_seq = prefix + str(num).zfill(padding) + suffix
                        exists_invoice = self.search([('invoice_number', '=',
                                                       last_seq)], limit=1)

                        if not exists_invoice:
                            raise exceptions.\
                                ValidationError(_("Any invoice found with last"
                                                  " number %s.") % last_seq)

    @api.multi
    def _send_invoice_to_sii(self):
        invoices = self.filtered(lambda x: x.state in
                                 ['open', 'in_payment', 'paid'] and
                                 x.sii_send_failed)
        invoices.write({'sii_send_failed': False})
        return super()._send_invoice_to_sii()

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None,
                        date=None, description=None, journal_id=None):
        vals = super(AccountInvoice, self)._prepare_refund(
            invoice, date_invoice, date, description, journal_id)

        if invoice.payment_term_id:
            vals['payment_term_id'] = invoice.payment_term_id.id
        return vals