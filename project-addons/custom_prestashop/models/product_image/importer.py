# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import tools
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class ProductImageMapper(Component):
    _inherit = 'prestashop.product.image.import.mapper'

    @mapping
    def file_db_store(self, record):
        image_data = tools.image_get_resized_images(record['content'], return_small=False)['image_medium']
        return {'file_db_store': image_data}

    @mapping
    def storage(self, record):
        # return {'storage': 'url'}
        return {'storage': 'db'}
