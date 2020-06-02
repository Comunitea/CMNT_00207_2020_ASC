# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class ProductImageMapper(Component):
    _inherit = "prestashop.product.image.import.mapper"

    @mapping
    def from_template(self, record):
        binder = self.binder_for("prestashop.product.template")
        template = binder.to_internal(record["id_product"], unwrap=True)
        name = "%s_%s" % (template.name, record["id_image"])
        image_exists = self.env["base_multi_image.image"].search(
            [("owner_id", "=", template.id), ("name", "=", name)]
        )
        if image_exists:
            return {"odoo_id": image_exists.id}
        return {"owner_id": template.id, "name": name}
