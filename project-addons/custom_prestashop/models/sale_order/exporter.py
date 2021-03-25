# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component


class PrestashopStandardPriceExporter(Component):
    _name = "prestashop.order_log.exporter"
    _inherit = "prestashop.exporter"
    _apply_on = ["prestashop.sale.order.log"]
    _usage = "order_log.exporter"

    def run(self, binding, **kwargs):
        """ Export the standard price of a product to PrestaShop """
        tracking_adapter = self.component(
            usage='backend.adapter',
            model_name='__not_exit_prestashop.orderodoo')
        tracking_adapter.create(
            {'id_order': binding.prestashop_id,
             'id_odoo': binding.odoo_id.id})
