# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

import logging

_logger = logging.getLogger(__name__)
try:
    from prestapyt import PrestaShopWebServiceError
except Exception:
    _logger.debug("Cannot import from `prestapyt`")


class ProductCombinationImporter(Component):
    _inherit = "prestashop.product.combination.importer"

    def _after_import(self, binding):
        super(ProductCombinationImporter, self)._after_import(binding)
        binding.odoo_id.with_context(active_test=True).recompute_packs()

    def set_variant_images(self, combinations):
        backend_adapter = self.component(
            usage="backend.adapter", model_name="prestashop.product.combination"
        )
        for combination in combinations:
            try:
                record = backend_adapter.read(combination["id"])
                associations = record.get("associations", {})
                ps_images = associations.get("images", {}).get(
                    self.backend_record.get_version_ps_key("image"), {}
                )
                binder = self.binder_for("prestashop.product.image")
                if not isinstance(ps_images, list):
                    ps_images = [ps_images]
                if ps_images:
                    ps_images = [ps_images[0]]
                if "id" in ps_images[0]:
                    images = [
                        binder.to_internal(x.get("id"), unwrap=True) for x in ps_images
                    ]
                else:
                    images = []
                if images:
                    product_binder = self.binder_for("prestashop.product.combination")
                    product_product = product_binder.to_internal(
                        combination["id"], unwrap=True
                    )
                    product_product.with_context(connector_no_export=True).write(
                        {"image_ids": [(6, 0, [x.id for x in images])]}
                    )
            except PrestaShopWebServiceError:
                # TODO: don't we track anything here? Maybe a checkpoint?
                pass


class ProductCombinationMapper(Component):
    _inherit = "prestashop.product.combination.mapper"

    @mapping
    def weight(self, record):
        combination_weight = float(record.get("weight", "0.0"))
        main_weight = (
            self.binder_for("prestashop.product.template")
            .to_internal(record["id_product"])
            .weight
        )
        weight = main_weight + combination_weight
        return {"weight": weight}

    @mapping
    def barcode(self, record):
        return {}
