# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create


class DeliveryCarrierMapper(Component):
    _inherit = "prestashop.delivery.carrier.import.mapper"

    @mapping
    def prestashop_unique_id(self, record):
        return {"prestashop_unique_id": record["id"]}

    @only_create
    @mapping
    def odoo_id(self, record):
        carrier_exists = self.env["delivery.carrier"].search(
            [("prestashop_unique_id", "=", record["id"])]
        )
        if carrier_exists:
            return {"odoo_id": carrier_exists.id}
        return {}
