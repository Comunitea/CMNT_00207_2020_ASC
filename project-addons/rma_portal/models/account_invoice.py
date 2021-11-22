# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AcccountInvoice(models.Model):
    _inherit = 'account.invoice'

    portal_state = fields.Selection(
        [('open', 'Open'), ('remitted', 'Remitted'), ('paid', 'Paid')],
        compute='compute_portal_state')

    @api.depends('state')
    def compute_portal_state(self):
        for invoice in self:
            if invoice.state == 'open':
                move_lines = invoice.sudo().mapped('move_id.line_ids.id')
                payment_lines = self.env['account.payment.line'].sudo().search_count(
                    [('move_line_id', 'in', move_lines)])
                if payment_lines:
                    invoice.portal_state = 'remitted'
                else:
                    invoice.portal_state = 'open'
            elif invoice.state == 'paid':
                invoice.portal_state = 'paid'
            else:
                invoice.portal_state = ''
