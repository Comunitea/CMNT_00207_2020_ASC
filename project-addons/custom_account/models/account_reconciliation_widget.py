# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class AccountReconciliationWidget(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def _get_possible_payment_orders_for_statement_line(self, st_line):
        """Find orders that might be candidates for matching a statement
        line.
        """
        return self.env['account.payment.order'].search([
            '|', ('total_company_currency', '=', st_line.amount),
            ('total_company_currency', '=', -st_line.amount),
            ('state', 'in', ['done', 'uploaded']),
        ])
