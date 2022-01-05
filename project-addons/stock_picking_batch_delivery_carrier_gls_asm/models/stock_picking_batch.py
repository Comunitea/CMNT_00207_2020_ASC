# Copyright 2020 Tecnativa - David Vidal
# Copyright (C) 2021 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models, api
from odoo.addons import decimal_precision as dp
from base64 import b64decode
from odoo.exceptions import UserError

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
            self.print_created_labels()

    @api.multi
    def remove_tracking_info(self):
        for pick in self.filtered(lambda x: x.carrier_id.delivery_type == "gls_asm"):
            pick.carrier_id.gls_asm_cancel_shipment(pick)
        return super().remove_tracking_info()
    
    def print_created_labels(self):
        if self.carrier_id.delivery_type == "gls_asm":
            self.ensure_one()

            if not self.carrier_id.gls_printer:
                return
            labels = self.env["ir.attachment"].search(
                [("res_id", "=", self.id), ("res_model", "=", self._name)]
            )
            for label in labels:
                if label.mimetype == "application/x-pdf" or label.mimetype == "application/pdf":
                    doc_format = "pdf"
                else:
                    doc_format = "raw"
                try:
                    self.carrier_id.gls_printer.print_document(
                        None, b64decode(label.datas), doc_format=doc_format
                    )
                except Exception as e:
                    self.message_post(
                        body=(_("Unable to print the label {}. Error: {}.".format(label.name, e))),
                    )
        else:
            return super(StockBatchPicking, self).print_created_labels()


class StockPicking(models.Model):

    _inherit = "stock.picking"

    def check_shipment_status(self):
        if self.carrier_id.delivery_type == "gls_asm":
            try:
                self.carrier_id.gls_asm_tracking_state_update(self)
            except Exception as e:
                self.message_post(
                    body=(_("Unable to check the state of the shipment. Error: {}.".format(e))),
                )
        else:
            return super().check_shipment_status()

