# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component


class PrestashopTrackingExporter(Component):
    _inherit = 'prestashop.stock.tracking.exporter'

    def _get_tracking(self):
        trackings = []
        for picking in self.binding.picking_ids:
            if picking.carrier_tracking_ref:
                trackings.append(picking.carrier_tracking_ref)
            elif picking.delivery_picking_id.carrier_tracking_ref:
                trackings.append(
                    picking.delivery_picking_id.carrier_tracking_ref)
        return ' '.join(trackings) if trackings else None
