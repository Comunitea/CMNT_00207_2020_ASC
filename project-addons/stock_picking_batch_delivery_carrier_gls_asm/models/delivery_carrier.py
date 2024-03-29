# Copyright 2020 Tecnativa - David Vidal
# Copyright (C) 2021 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models
from xml.sax.saxutils import escape
from .gls_asm_request import GlsAsmRequest
from .gls_asm_request import (
    GLS_ASM_SERVICES, GLS_SHIPPING_TIMES, GLS_POSTAGE_TYPE,
    GLS_DELIVERY_STATES_STATIC)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[("gls_asm", "GLS ASM")])
    gls_asm_uid = fields.Char(
        string="GLS UID",
    )
    gls_asm_service = fields.Selection(
        selection=GLS_ASM_SERVICES,
        string="GLS Service",
        help="Set the contracted GLS Service",
        default="1",  # Courier
    )
    gls_asm_shiptime = fields.Selection(
        selection=GLS_SHIPPING_TIMES,
        string="Shipping Time",
        help="Set the desired GLS shipping time for this carrier",
        default="0",  # 10h
    )
    gls_asm_postage_type = fields.Selection(
        selection=GLS_POSTAGE_TYPE,
        string="Postage Type",
        help="Postage type, usually 'Prepaid'",
        default="P",
    )
    gls_last_request = fields.Text(
        string="Last GLS xml request",
        help="Used for issues debugging",
        readonly=True,
    )
    gls_last_response = fields.Text(
        string="Last GLS xml response",
        help="Used for issues debugging",
        readonly=True,
    )
    gls_printer = fields.Many2one('printing.printer')

    def _gls_asm_uid(self):
        """The carrier can be put in test mode. The tests user must be set.
           A default given by GLS is put in the config parameter data """
        self.ensure_one()
        uid = (
            self.gls_asm_uid if self.prod_environment else
            self.env['ir.config_parameter'].sudo().get_param(
                'delivery_gls_asm.api_user_demo', ''))
        return uid

    def gls_asm_get_tracking_link(self, batch):
        """Provide tracking link for the customer"""
        tracking_url = ("http://www.asmred.com/extranet/public/"
                        "ExpedicionASM.aspx?codigo={}&cpDst={}")
        return tracking_url.format(
            batch.carrier_tracking_ref, batch.partner_id.zip)

    def _prepare_gls_asm_shipping(self, batch):
        """Convert batch values for asm api
        :param batch record with batch to send
        :returns dict values for the connector
        """
        self.ensure_one()
        # A picking can be delivered from any warehouse
        sender_partner = (
            batch.picking_type_id.warehouse_id.partner_id or
            batch.company_id.partner_id)
        return {
            "fecha": fields.Date.today().strftime("%d/%m/%Y"),
            "portes": self.gls_asm_postage_type,
            "servicio": self.gls_asm_service,
            "horario": self.gls_asm_shiptime,
            "bultos": batch.carrier_packages or 1,
            "peso": round(batch.carrier_weight, 3) or 1,
            "volumen": "",  # [optional] Volume, in m3
            "declarado": "",  # [optional]
            "dninomb": "0",  # [optional]
            "fechaentrega": "",  # [optional]
            "retorno": "0",  # [optional]
            "pod": "N",  # [optional]
            "podobligatorio": "N",  # [deprecated]
            "remite_plaza": "",  # [optional] Origin agency
            "remite_nombre": escape(sender_partner.name),
            "remite_direccion": escape(sender_partner.street) or "",
            "remite_poblacion": sender_partner.city or "",
            "remite_provincia": sender_partner.state_id.name or "",
            "remite_pais": "34",  # [mandatory] always 34=Spain
            "remite_cp": sender_partner.zip or "",
            "remite_telefono": sender_partner.phone or "",
            "remite_movil": sender_partner.mobile or "",
            "remite_email": sender_partner.email or "",
            "remite_departamento": "",
            "remite_nif": sender_partner.vat or "",
            "remite_observaciones": "",
            "destinatario_codigo": "",
            "destinatario_plaza": "",
            "destinatario_nombre": (
                escape(batch.partner_id.name)
                or escape(batch.partner_id.commercial_partner_id.name)
            ),
            "destinatario_direccion": batch.partner_id.street or "",
            "destinatario_poblacion": batch.partner_id.city or "",
            "destinatario_provincia": batch.partner_id.state_id.name or "",
            "destinatario_pais": (
                batch.partner_id.country_id.phone_code or ""),
            "destinatario_cp": batch.partner_id.zip,
            "destinatario_telefono": batch.partner_id.phone or batch.partner_id.commercial_partner_id.phone or batch.partner_id.mobile or batch.partner_id.commercial_partner_id.mobile or "",
            "destinatario_movil": batch.partner_id.mobile or batch.partner_id.commercial_partner_id.mobile or batch.partner_id.phone or batch.partner_id.commercial_partner_id.phone or "",
            "destinatario_email": batch.partner_id.email or batch.partner_id.commercial_partner_id.email or "",
            "destinatario_observaciones": "",
            "destinatario_att": "",
            "destinatario_departamento": "",
            "destinatario_nif": "",
            "referencia_c": escape(batch.name),  # Our unique reference
            "referencia_0": "",  # Not used if the above is set
            "importes_debido": "0",  # The customer pays the shipping
            "importes_reembolso": batch.pdo_quantity if batch.payment_on_delivery else "",  # TODO: Support Cash On Delivery
            "seguro": "0",  # [optional]
            "seguro_descripcion": "",  # [optional]
            "seguro_importe": "",  # [optional]
            "etiqueta": "PDF",  # Get Label in response
            "etiqueta_devolucion": "PDF",
            # [optional] GLS Customer Code
            # (when customer have several codes in GLS)
            "cliente_codigo": "",
            "cliente_plaza": "",
            "cliente_agente": "",
        }

    def gls_asm_send_shipping(self, batchs):
        """Send the package to GLS
        :param batchs: A recordset of batchs
        :return list: A list of dictionaries although in practice it's
        called one by one and only the first item in the dict is taken. Due
        to this design, we have to inject vals in the context to be able to
        add them to the message.
        """
        gls_request = GlsAsmRequest(self._gls_asm_uid())
        result = []
        for batch in batchs:
            try:
                vals = self._prepare_gls_asm_shipping(batch)
                vals.update({"tracking_number": False, "exact_price": 0})
                response = gls_request._send_shipping(vals)
                self.gls_last_request = response and response.get(
                    "gls_sent_xml", "")
                self.gls_last_response = response or ""
                if not response or response.get("_return", -1) < 0:
                    result.append(vals)
                    continue
                # For compatibility we provide this number although we get
                # two more codes: codbarras and uid
                vals["tracking_number"] = response.get("_codexp")
                batch.carrier_tracking_ref = response.get("_codbarras")
                # We post an extra message in the chatter with the barcode and the
                # label because there's clean way to override the one sent by core.
                body = _(
                    "GLS Shipping extra info:\n"
                    "barcode: %s") % response.get("_codbarras")
                attachment = []
                if response.get("gls_label"):
                    attachment = [(
                        "gls_label_{}.pdf".format(response.get("_codbarras")),
                        response.get("gls_label")
                    )]
                batch.message_post(body=body, attachments=attachment)
                result.append(vals)
                if batch.carrier_tracking_ref:
                    batch.picking_ids.update({
                        'carrier_tracking_ref': batch.carrier_tracking_ref
                    })
                # Adding this to the stock.picking mail.template:
                #
                #% if object.batch_id and object.batch_id.gls_extra_batch_ids:
                #    % for batch in object.batch_id.gls_extra_batch_ids:
                #        % if batch.carrier_tracking_url:
                #            ${batch.carrier_tracking_url}<br/>
                #        % endif
                #    % endfor
                #% endif
                #
                # So where are not using this anymore. 
                #if batch.gls_origin_batch_id:
                #    template = self.env.ref(
                #        "stock_picking_batch_delivery_carrier_gls_asm.gls_extra_batch_mail_template"
                #    )
                #    batch.with_context(force_send=True).message_post_with_template(
                #        template.id,
                #        composition_mode="mass_mail",
                #    )
            except Exception as e:
                body = _("Error retrieving the label: {}".format(e))
                batch.message_post(body=body)
                continue
        return result

    def gls_asm_tracking_state_update(self, pick):
        """Tracking state update"""
        self.ensure_one()
        if not pick.carrier_tracking_ref:
            return
        gls_request = GlsAsmRequest(self._gls_asm_uid())
        tracking_states = gls_request._get_tracking_states(
            pick.carrier_tracking_ref)
        if not tracking_states:
            return
        tracking_state_history = "\n".join([
            "%s - [%s] %s" % (
                t.get("fecha"), t.get("codigo"), t.get("evento"))
            for t in tracking_states
        ])

        tracking = tracking_states.pop()
        tracking_state = "[{}] {}".format(
            tracking.get("codigo"), tracking.get("evento"))
        delivery_state = GLS_DELIVERY_STATES_STATIC.get(
            tracking.get("codigo"), 'incidence')
        
        body = _("Tracking state history:\n {}.\n Tracking state: {}. \n Delivery state: {}.".format(
            tracking_state_history,
            tracking_state,
            delivery_state,
        ))

        pick.message_post(body=body)
        
        if delivery_state == 'customer_delivered':
            pick.delivered = True

    def gls_asm_cancel_shipment(self, batchs):
        """Cancel the expedition"""
        gls_request = GlsAsmRequest(self._gls_asm_uid())
        for batch in batchs.filtered("carrier_tracking_ref"):
            response = gls_request._cancel_shipment(
                batch.carrier_tracking_ref)
            self.gls_last_request = response and response.get(
                "gls_sent_xml", "")
            self.gls_last_response = response or ""
            if not response or response.get("_return") < 0:
                msg = (_(
                    "GLS Cancellation failed with reason: %s") %
                    response.get("value", "Connection Error"))
                batch.message_post(body=msg)
                continue
            batch.message_post(body=_(
                "GLS Expedition with reference %s cancelled") %
                batch.carrier_tracking_ref)
            batch.carrier_tracking_ref = False

    def gls_asm_rate_shipment(self, order):
        """There's no public API so another price method should be used"""
        raise NotImplementedError(_("""
            GLS ASM API doesn't provide methods to compute delivery rates, so
            you should relay on another price method instead or override this
            one in your custom code.
        """))

    def gls_asm_get_label(self, carrier_tracking_ref):
        """Generate label for picking
        :param picking - stock.picking record
        :returns pdf file
        """
        self.ensure_one()
        if not carrier_tracking_ref:
            return False
        gls_request = GlsAsmRequest(self._gls_asm_uid())
        label = gls_request._shipping_label(carrier_tracking_ref)
        if not label:
            return False
        return label

    def action_get_manifest(self):
        """Action to launch the manifest wizard"""
        self.ensure_one()
        wizard = self.env["gls.asm.minifest.wizard"].create({
            "carrier_id": self.id})
        view_id = self.env.ref(
            "stock_picking_batch_delivery_carrier_gls_asm.delivery_manifest_wizard_form"
        ).id
        return {
            "name": _("GLS Manifest"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "gls.asm.minifest.wizard",
            "view_id": view_id,
            "views": [(view_id, "form")],
            "target": "new",
            "res_id": wizard.id,
            "context": self.env.context,
        }
