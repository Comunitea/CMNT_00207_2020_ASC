# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class ProductImageMapper(Component):
    _inherit = 'prestashop.product.image.import.mapper'

    @mapping
    def file_db_store(self, record):
        return {'file_db_store': record['content']}

    @mapping
    def storage(self, record):
        # return {'storage': 'url'}
        return {'storage': 'db'}
