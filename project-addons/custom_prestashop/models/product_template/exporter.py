# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import FailedJobError


class PrestashopStandardPriceExporter(Component):
    _name = "prestashop.standard_price.exporter"
    _inherit = "prestashop.exporter"
    _apply_on = ["prestashop.product.template"]
    _usage = "standard_price.exporter"

    def run(self, binding, **kwargs):
        """ Export the standard price of a product to PrestaShop """
        vals = self.component(usage="backend.adapter").read(binding.prestashop_id)
        no_pack_variants = [x for x in binding.odoo_id.product_variant_ids if not x.pack_product]
        if len(no_pack_variants) != 1:
            raise Exception('Different base variants for prestashop product {}'.format(binding.prestashop_id))
        vals.pop("manufacturer_name")
        vals.pop("quantity")
        vals["wholesale_price"] = no_pack_variants[0].standard_price
        self.component(usage="backend.adapter").write(binding.prestashop_id, vals)
