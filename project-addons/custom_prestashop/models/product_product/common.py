# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ProductProduct(models.Model):

    _inherit = "product.product"
    pack_product = fields.Boolean(compute='_compute_pack_product', store=True)

    @api.depends('attribute_value_ids.product_id')
    def _compute_pack_product(self):
        for product in self:
            if any(product.mapped('attribute_value_ids.product_id')):
                product.pack_product = True
            else:
                product.pack_product = False

    def recompute_packs(self):
        for product in self:
            create_bom = False
            bundle_products = {}
            for attr_value in product.attribute_value_ids:
                if attr_value.product_id:
                    bundle_products[attr_value.product_id] = 1
            if bundle_products:
                base_product = product.product_tmpl_id.product_variant_ids.filtered(
                    lambda r: not r.mapped("attribute_value_ids.product_id")
                )
                if base_product:
                    bundle_products[base_product[0]] = 1
                product_bom = self.env["mrp.bom"].search(
                    [("product_id", "=", product.id)]
                )
                if product_bom:
                    current_bom = product_bom
                    for line in current_bom.bom_line_ids:
                        if (
                            line.product_id not in bundle_products.keys()
                            or line.product_qty != bundle_products[line.product_id]
                        ):
                            product_bom.write({"active": False})
                            create_bom = True
                            break
                    for in_product in bundle_products.keys():
                        if in_product not in current_bom.mapped(
                            "bom_line_ids.product_id"
                        ):
                            product_bom.write({"active": False})
                            create_bom = True
                            break
                else:
                    create_bom = True
                if create_bom:
                    self.env["mrp.bom"].create(
                        {
                            "product_tmpl_id": product.product_tmpl_id.id,
                            "product_id": product.id,
                            "type": "phantom",
                            "bom_line_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": x.id,
                                        "product_qty": bundle_products[x],
                                    },
                                )
                                for x in bundle_products.keys()
                            ],
                        }
                    )

    def _set_standard_price(self):
        res = super()._set_standard_price()
        for record in self.mapped('product_tmpl_id'):
            self._event("on_standard_price_changed").notify(record)
        return res
