# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create


class ProductBrandMapper(Component):
    _name = 'prestashop.product.brand.mapper'
    _inherit = 'prestashop.import.mapper'
    _apply_on = 'prestashop.product.brand'

    direct = [
        ('name', 'name'),
    ]

    @mapping
    def prestashop_unique_id(self, record):
        return {"prestashop_unique_id": record["id"]}

    @only_create
    @mapping
    def odoo_id(self, record):
        brand_exists = self.env["product.brand"].search(
            [("prestashop_unique_id", "=", record["id"])]
        )
        if brand_exists:
            return {"odoo_id": brand_exists.id}
        return {}


class ProductBrandImporter(Component):
    """ Import one record """
    _name = 'prestashop.product.brand.importer'
    _inherit = 'prestashop.importer'
    _apply_on = 'prestashop.product.brand'


class ProductBrandBatchImporter(Component):
    _name = 'prestashop.product.brand.batch.importer'
    _inherit = 'prestashop.direct.batch.importer'
    _apply_on = 'prestashop.product.brand'
