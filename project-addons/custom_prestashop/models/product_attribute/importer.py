# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class ProductCombinationOptionImporter(Component):
    _inherit = "prestashop.product.combination.option.importer"

    def _import_values(self, attribute_binding):
        record = self.prestashop_record
        option_values = (
            record.get("associations", {})
            .get("product_option_values", {})
            .get(
                self.backend_record.get_version_ps_key("product_option_value"),
                [],
            )
        )
        if not isinstance(option_values, list):
            option_values = [option_values]
        for option_value in option_values:
            self._import_dependency(
                option_value["id"],
                "prestashop.product.combination.option.value",
                always=True,
            )


class ProductCombinationOptionValueImporter(Component):
    _inherit = "prestashop.product.combination.option.value.importer"

    def _import_dependencies(self):
        record = self.prestashop_record
        if record.get("id_product") != "0":
            self._import_dependency(
                record["id_product"], "prestashop.product.template"
            )


class ProductCombinationOptionValueMapper(Component):
    _inherit = "prestashop.product.combination.option.value.mapper"

    @mapping
    def product_id(self, record):
        if record.get("id_product") != "0":
            product = self.binder_for(
                "prestashop.product.template"
            ).to_internal(record["id_product"], unwrap=True)
            return {"product_id": product.product_variant_ids[0].id}
        return {}


class ProductAttributeBatchImporter(Component):
    """ Import the PrestaShop product attributes.
    """

    _name = "prestashop.product.combination.option.delayed.batch.importer"
    _inherit = "prestashop.delayed.batch.importer"
    _apply_on = "prestashop.product.combination.option"

    _model_name = ["prestashop.product.combination.option"]

    def run(self, filters=None, **kwargs):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search(filters=filters)
        _logger.info(
            "search for prestashop product attributes %s returned %s",
            filters,
            record_ids,
        )
        for record_id in record_ids:
            self._import_record(record_id, **kwargs)
