##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2020 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
#    Vicente Ángel Gutiérrez <vicente@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See thefire
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from base64 import b64decode
from odoo.addons import decimal_precision as dp


class StockBatchPicking(models.Model):

    _inherit = "stock.picking.batch"

    carrier_id = fields.Many2one("delivery.carrier", "Carrier", ondelete="cascade")
    service_code = fields.Many2one(
        "delivery.carrier.service", string="Carrier service code"
    )
    carrier_tracking_ref = fields.Char("Tracking Code")
    carrier_account_id = fields.Many2one(
        "carrier.account", related="carrier_id.account_id"
    )
    shipment_reference = fields.Char("Shipment Reference")
    payment_on_delivery = fields.Boolean("Payment on delivery")
    pdo_quantity = fields.Float("PDO amount", digits=dp.get_precision("Product Price"))
    declared_value = fields.Float("Declared value", digits=dp.get_precision("Product Price"))
    needs_signature = fields.Boolean(
        related="carrier_id.needs_signature", readonly=True
    )
    tracking_url = fields.Char("Tracking URL", compute="_compute_tracking_url")
    failed_shipping = fields.Boolean("Failed Shipping", default=False)
    delivery_note = fields.Char(compute="_compute_delivery_note")
    carrier_weight = fields.Float(default=0)
    carrier_packages = fields.Integer(default=0)
    partner_id = fields.Many2one("res.partner", string="Empresa")
    carrier_tracking_url = fields.Char(string='Tracking URL', compute='_compute_carrier_tracking_url')

    @api.depends('carrier_id', 'carrier_tracking_ref')
    def _compute_carrier_tracking_url(self):
        for batch in self:
            batch.carrier_tracking_url = batch.carrier_id.get_tracking_link(batch) if batch.carrier_id and batch.carrier_tracking_ref else False

    @api.multi
    def get_pdo_quantity(self):
        for batch in self:
            pickings_total_value = 0.0
            for pick in batch.picking_ids:                    
                for line in pick.move_line_ids.mapped('sale_line'):
                    pickings_total_value += line.price_total
                if pick.sale_id and (not pick.sale_id.paid_shipping_batch_id or pick.sale_id.paid_shipping_batch_id == batch):
                    pickings_total_value += pick.sale_id.shipping_amount_total
                if pick.sale_id:
                    discount = pick.sale_id.order_line.filtered(lambda x: x.product_id.type == 'service' and x.price_total < 0.0)
                    for dis in discount:
                        pickings_total_value += dis.price_total
            batch.pdo_quantity = pickings_total_value
            batch.declared_value = pickings_total_value

    @api.model
    def create(self, vals):
        if vals.get("carrier_id"):
            carrier_id = self.env["delivery.carrier"].search(
                [("id", "=", vals.get("carrier_id"))]
            )
            if carrier_id and carrier_id.service_code:
                vals["service_code"] = carrier_id.service_code.id
        if vals.get("payment_on_delivery", False):
            self.get_pdo_quantity()
        return super(StockBatchPicking, self).create(vals)

    @api.onchange("service_code")
    def _onchange_service_code(self):
        if self.service_code:
            for pick in self.picking_ids:
                pick.write({"carrier_service": self.service_code.id})

    @api.depends("sale_ids")
    def _compute_delivery_note(self):
        for batch in self:
            delivery_note = ""
            for sale in batch.sale_ids:
                delivery_note += "{} ".format(sale.note)
            if delivery_note.strip() == "":
                delivery_note = "N/A"
            batch.delivery_note = delivery_note[:45]

    @api.model
    def button_validate_apk(self, vals):
        batch_id = self.browse(vals.get("id", False))
        res = super(StockBatchPicking, self).button_validate_apk(vals)
        if batch_id.picking_type_id.code == "outgoing":
            try:
                self.env.ref("stock.action_report_delivery").print_document(
                    batch_id.picking_ids._ids
                )
            except Exception:
                batch_id.message_post('Ha fallado la impresión del albarán')
            try:
                batch_id.send_shipping()
                batch_id.failed_shipping = False
            except Exception:
                batch_id.failed_shipping = True
        return res

    @api.depends("carrier_id", "carrier_tracking_ref")
    def _compute_tracking_url(self):
        for batch in self:
            batch.tracking_url = (
                batch.carrier_id.get_tracking_link(batch)
                if batch.carrier_id and batch.carrier_tracking_ref
                else False
            )

    @api.multi
    def write(self, vals):
        res = super().write(vals)
        if vals.get('carrier_id'):
            for batch in self:
                if batch.carrier_id:
                    batch.service_code = batch.carrier_id.service_code
                    for pick in batch.picking_ids:
                        pick.write(
                            {
                                "carrier_id": batch.carrier_id.id,
                                "carrier_service": batch.carrier_id.service_code.id,
                            }
                        )
        if vals.get("carrier_tracking_ref", False):
            for batch in self:
                if batch.carrier_tracking_ref:
                    for pick in batch.picking_ids:
                        pick.write({"carrier_tracking_ref": batch.carrier_tracking_ref})
        
        for batch in self:
            if batch.payment_on_delivery and not vals.get("pdo_quantity"):
                batch.get_pdo_quantity()
        return res

    @api.multi
    def remove_tracking_info(self):
        for batch in self:
            batch.update({"carrier_tracking_ref": False, "shipment_reference": False})

            for pick in batch.picking_ids:
                pick.write({"carrier_tracking_ref": False})

            self.env["ir.attachment"].search(
                [
                    ("name", "=", "Label: {}".format(batch.name)),
                    ("res_id", "=", batch.id),
                    ("res_model", "=", self._name),
                ]
            ).unlink()

            if batch.payment_on_delivery:
                batch.mark_as_unpaid_shipping()

    def send_shipping(self):
        if self.carrier_tracking_ref:
            return
        self.check_delivery_address()
        if self.payment_on_delivery:
            self.mark_as_paid_shipping()

    def track_request(self):
        return True

    def check_delivery_address(self):
        if not self.partner_id.city:
            raise UserError(_("Partner address is not complete (City missing)."))
        if not self.partner_id.street:
            raise UserError(_("Partner address is not complete (Street missing)."))
        if not (
            self.partner_id.phone
            or self.partner_id.mobile
            or self.partner_id.commercial_partner_id.phone
            or self.partner_id.commercial_partner_id.mobile
        ):
            raise UserError(
                _("Partner address is not complete (Needs a phone or mobile phone).")
            )
        if not self.partner_id.country_id:
            raise UserError(_("Partner address is not complete (Country missing)."))
        if not (self.partner_id.email or self.partner_id.commercial_partner_id.email):
            raise UserError(_("Partner address is not complete (Email missing)."))
        if not self.partner_id.zip:
            raise UserError(_("Partner address is not complete (Zip code missing)."))

    def print_created_labels(self):
        self.ensure_one()

        if not self.carrier_id.account_id.printer:
            return
        labels = self.env["ir.attachment"].search(
            [("res_id", "=", self.id), ("res_model", "=", self._name)]
        )
        for label in labels:
            if label.mimetype == "application/x-pdf":
                doc_format = "pdf"
            else:
                doc_format = "raw"
            try:
                self.carrier_id.account_id.printer.print_document(
                    None, b64decode(label.datas), doc_format=doc_format
                )
            except Exception as e:
                self.message_post(
                    body=(_("Unable to print the label {}. Error: {}.".format(label.name, e))),
                )

    def get_state_id(self, partner_id):
        if partner_id.country_id and partner_id.zip:
            city_zip = self.env["res.city.zip"].search(
                [
                    ("name", "=", partner_id.zip),
                    ("city_id.country_id", "=", partner_id.country_id.id),
                ],
                limit=1,
            )
            if not city_zip:
                # Portugal
                city_zip = self.env["res.city.zip"].search(
                    [
                        ("name", "=", partner_id.zip.replace(" ", "-")),
                        ("city_id.country_id", "=", partner_id.country_id.id),
                    ],
                    limit=1,
                )
                if not city_zip:
                    # Portugal 2
                    city_zip = self.env["res.city.zip"].search(
                        [
                            (
                                "name",
                                "=",
                                partner_id.zip[:4] + "-" + partner_id.zip[4:],
                            ),
                            ("city_id.country_id", "=", partner_id.country_id.id),
                        ],
                        limit=1,
                    )
            if city_zip:
                return {"state_id": city_zip.city_id.state_id.id}

    @api.multi
    def mark_as_paid_shipping(self):
        for batch in self:
            for sale in batch.picking_ids.mapped("sale_id"):
                if not sale.paid_shipping_batch_id:
                    sale.paid_shipping_batch_id = batch.id

    @api.multi
    def mark_as_unpaid_shipping(self):
        for batch in self:
            for sale in batch.picking_ids.mapped("sale_id"):
                if sale.paid_shipping_batch_id and sale.paid_shipping_batch_id.id == batch.id:
                    sale.paid_shipping_batch_id = None

class StockPicking(models.Model):

    _inherit = "stock.picking"

    payment_on_delivery = fields.Boolean("Payment on delivery")

    @api.multi
    def send_to_shipper(self):
        if not self.batch_id:
            return super().send_to_shipper()

    def onchange_partner_id_or_carrier_id(self):
        return True

    @api.model
    def create(self, vals):
        if vals.get("origin"):
            sale_id = self.env["sale.order"].search([("name", "=", vals.get("origin"))])
            if sale_id and sale_id.payment_mode_id.payment_on_delivery:
                vals["payment_on_delivery"] = True
        return super(StockPicking, self).create(vals)


class CarrierAccount(models.Model):
    _inherit = "carrier.account"

    delivery_carrier = fields.Selection([("none", "None")])
