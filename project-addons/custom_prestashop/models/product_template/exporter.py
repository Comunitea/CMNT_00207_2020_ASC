# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component


class PrestashopStandardPriceExporter(Component):
    _name = "prestashop.standard_price.exporter"
    _inherit = "prestashop.exporter"
    _apply_on = ["prestashop.product.template"]
    _usage = "standard_price.exporter"

    def run(self, binding, **kwargs):
        """ Export the standard price of a product to PrestaShop """
        return True
        no_pack_variants = [
            x for x in binding.odoo_id.product_variant_ids if not x.pack_product
        ]
        if len(no_pack_variants) != 1:
            raise Exception(
                "Different base variants for prestashop product {}".format(
                    binding.prestashop_id
                )
            )
        vals = self.component(usage="backend.adapter").read(binding.prestashop_id)
        vals.pop("manufacturer_name")
        vals.pop("quantity")
        vals["wholesale_price"] = no_pack_variants[0].standard_price
        self.component(usage="backend.adapter").write(binding.prestashop_id, vals)


class ProductInventoryExporter(Component):
    _inherit = "prestashop.product.template.inventory.exporter"

    def get_filter(self, template):
        binder = self.binder_for()
        prestashop_id = binder.to_external(template)
        return {"filter[id_product]": prestashop_id}

    def get_quantity_vals(self, template):
        vals = super().get_quantity_vals(template=template)
        vals.update({
            'estimated_stock_available': int(template.estimated_stock_available),
            'date_estimated_stock': template.date_estimated_stock,
            'date_estimated_stock_available': template.date_estimated_stock_available
        })
        return vals