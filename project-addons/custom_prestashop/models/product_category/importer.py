# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class ProductCategoryMapper(Component):
    _inherit = "prestashop.product.category.import.mapper"

    @mapping
    def odoo_id(self, record):
        if record["name"]:
            category_exists = self.env["prestashop.product.category"].search(
                [("prestashop_id", "=", record["id"])]
            )
            if category_exists:
                if len(category_exists.mapped("odoo_id")) == 1:
                    return {"odoo_id": category_exists.mapped("odoo_id").id}
        return {}
