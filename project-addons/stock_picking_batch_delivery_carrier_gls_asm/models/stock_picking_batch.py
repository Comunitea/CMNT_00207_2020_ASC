# Copyright 2020 Tecnativa - David Vidal
# Copyright (C) 2021 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models, api
from odoo.addons import decimal_precision as dp
from base64 import b64decode
from odoo.exceptions import UserError
import math

class StockBatchPicking(models.Model):
    _inherit = "stock.picking.batch"

    source_sale_id = fields.Many2one('sale.order', string='Venta')
    gls_origin_batch_id = fields.Many2one('stock.picking.batch', string='GLS Origin Batch')
    gls_extra_batch_ids = fields.One2many('stock.picking.batch', 'gls_origin_batch_id',  string='GLS Extra Batchs')

    @api.multi
    def gls_divide_in_packages(self):
        for batch in self:
            if round(batch.carrier_weight/batch.carrier_packages, 3) > 31.5:
                batch.carrier_packages = math.ceil(batch.carrier_weight/31.5)
            packages_to_create = batch.carrier_packages
            each_package_weight = round(batch.carrier_weight/batch.carrier_packages, 3)
            created_packages = 1
            while created_packages < packages_to_create:
                values = {
                    'name': "{}-{}".format(batch.name, created_packages),
                    'user_id': batch.user_id.id,
                    'carrier_packages': 1,
                    'carrier_weight': each_package_weight,
                    'notes': batch.notes,
                    'source_sale_id': batch.sale_id.id if batch.sale_id else None,
                    'gls_origin_batch_id': batch.id,
                }
                
                new_batch = batch.copy(
                    default=values
                )

                new_batch.picking_type_id = batch.picking_type_id.id
                
                body=_("New batch created: <a href='{}' target='_blank'>{}</a>".format(
                    new_batch.get_base_url() + new_batch.get_backend_url(),
                    new_batch.name
                ))
                batch.message_post(
                    body=body
                )
                created_packages += 1
            batch.carrier_weight = each_package_weight
            batch.carrier_packages = 1
            batch.gls_extra_batch_ids.write({'state': 'done'})
    
    @api.multi
    def get_base_url(self):
        """Get the base URL for the current batch."""
        self.ensure_one()
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    
    @api.multi
    def get_backend_url(self):
        """Get the backend URL for the current batch."""
        self.ensure_one()
        return '/web#id={}&model=stock.picking.batch&view_type=form'.format(self.id)
    
    @api.multi
    def _compute_order_ids(self):
        super(StockBatchPicking, self)._compute_order_ids()
        for batch in self:
            if len(batch.picking_ids) == 0 and batch.source_sale_id and not batch.sale_id:
                batch.sale_id = batch.source_sale_id

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
        if (self.carrier_id.delivery_type == "gls_asm"):
            # We need to divide the package if the destiny country is not Spain/Portugal and
            # the number of packages is > 1 or the weight per package is > 31.5
            if self.carrier_packages < 1:
                self.carrier_packages = 1
            if self.partner_id.country_id and not self.partner_id.country_id.code == 'ES' and (
                self.carrier_packages > 1
                or round(self.carrier_weight / self.carrier_packages, 3) > 31.5
            ):
                self.gls_divide_in_packages()
            # We send first the extra batchs
            # This way we can add the extra batchs tracking ref to the mail.template
            if self.gls_extra_batch_ids:
                not_sent_batchs = self.gls_extra_batch_ids.filtered(
                    lambda x: not x.carrier_tracking_ref
                )
                self.carrier_id.gls_asm_send_shipping(not_sent_batchs)
                for batch in not_sent_batchs:
                    batch.print_created_labels()
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

