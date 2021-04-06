# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component


class ProductBrandMapper(Component):
    _name = 'prestashop.product.brand.mapper'
    _inherit = 'prestashop.import.mapper'
    _apply_on = 'prestashop.product.brand'

    direct = [
        ('name', 'name'),
    ]


class ProductBrandImporter(Component):
    """ Import one record """
    _name = 'prestashop.product.brand.importer'
    _inherit = 'prestashop.importer'
    _apply_on = 'prestashop.product.brand'


class ProductBrandBatchImporter(Component):
    _name = 'prestashop.product.brand.batch.importer'
    _inherit = 'prestashop.direct.batch.importer'
    _apply_on = 'prestashop.product.brand'
