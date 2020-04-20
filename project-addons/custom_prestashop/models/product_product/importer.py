# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class ProductCombinationImporter(Component):
    _inherit = "prestashop.product.combination.importer"

    def _after_import(self, binding):
        super(ProductCombinationImporter, self)._after_import(binding)
        binding.odoo_id.with_context(active_test=True).recompute_packs()


class ProductCombinationMapper(Component):
    _inherit = 'prestashop.product.combination.mapper'

    @mapping
    def weight(self, record):
        combination_weight = float(record.get('weight', '0.0'))
        main_weight = self.binder_for('prestashop.product.template').to_internal(record['id_product']).weight
        weight = main_weight + combination_weight
        return {'weight': weight}
