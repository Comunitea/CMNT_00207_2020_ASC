# Copyright 2020 Tecnativa - David Vidal
# Copyright (C) 2021 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models, api
from odoo.addons import decimal_precision as dp


class StockBatchPicking(models.Model):
    _inherit = "stock.picking.batch"

    def gls_asm_get_label(self):
        """Get GLS Label for this picking expedition"""
        self.ensure_one()
        if (self.delivery_type != "gls_asm" or not
                self.carrier_tracking_ref):
            return
        pdf = self.carrier_id.gls_asm_get_label(
            self.carrier_tracking_ref)
        label_name = "gls_{}.pdf".format(self.carrier_tracking_ref)
        self.message_post(
            body=(_("GLS label for %s") % self.carrier_tracking_ref),
            attachments=[(label_name, pdf)],
        )
    
    def send_shipping(self):
        super(StockBatchPicking, self).send_shipping()
        if self.carrier_id.delivery_type == "gls_asm":
            self.carrier_id.gls_asm_send_shipping(self)

    @api.multi
    def remove_tracking_info(self):
        for pick in self.filtered(lambda x: x.carrier_id.delivery_type == "gls_asm"):
            pick.carrier_id.gls_asm_cancel_shipment(pick)
        return super().remove_tracking_info()


class StockPicking(models.Model):

    _inherit = "stock.picking"

    def check_shipment_status(self):
        if self.carrier_id.delivery_type == "gls_asm":
            self.carrier_id.gls_asm_tracking_state_update(self)
        else:
            return super().check_shipment_status()

