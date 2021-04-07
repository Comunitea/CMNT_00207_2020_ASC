# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
import odoo.addons.decimal_precision as dp


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    product_brand_id = fields.Many2one(
        comodel_name='product.brand',
        string='Brand',
    )

    def _select(self):
        res = super()._select()
        res += ", t.product_brand_id AS product_brand_id"
        return res

    def _group_by(self):
        res = super()._group_by()
        res += ", t.product_brand_id"
        return res
