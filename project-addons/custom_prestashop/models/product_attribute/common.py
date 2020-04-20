# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    product_id = fields.Many2one("product.product")
    variant_ids = fields.Many2many("product.product")

    def write(self, vals):
        for value in self:
            old_product = value.product_id.id
            res = super(ProductAttributeValue, value).write(vals)
            if (
                "product_id" in vals
                and vals["product_id"]
                and vals["product_id"] != old_product
            ):
                value.variant_ids.recompute_packs()
        return res
