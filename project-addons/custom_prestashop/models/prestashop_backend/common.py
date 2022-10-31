# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class PrestashopBackend(models.Model):
    _inherit = "prestashop.backend"

    sent_state = fields.Many2one("sale.order.state")
    delivered_state = fields.Many2one("sale.order.state")
    early_payment_term = fields.Many2one('account.payment.term')
    backend_export_qty= fields.Boolean("Export qty?", default=False)

    def import_attributes(self):
        for backend_record in self:
            self.env["prestashop.product.combination.option"].with_delay().import_batch(
                backend_record
            )
        return True

    def import_brands(self):
        for backend_record in self:
            self.env['prestashop.product.brand'].with_context(company_id=backend_record.company_id.id).with_delay().import_batch(
                backend_record,
            )
        return True

    def import_stock_qty(self):
        raise Exception()
