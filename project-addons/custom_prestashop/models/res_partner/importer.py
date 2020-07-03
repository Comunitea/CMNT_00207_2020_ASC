# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.exception import MappingError
from odoo.addons.connector.components.mapper import mapping, only_create


class PartnerImportMapper(Component):
    _inherit = "prestashop.res.partner.mapper"

    @mapping
    @only_create
    def property_payment_term_id(self, record):
        if record.get("plazo") and record.get("plazo") != "0":
            payment_term = self.env["account.payment.term"].search(
                [("prestashop_name", "=", record.get("plazo"))]
            )
            if not payment_term:
                raise MappingError(
                    _("Payment term with {} prestashop name not found.").format(
                        record.get("plazo")
                    )
                )
            return {"property_payment_term_id": payment_term.id}

    @mapping
    def customer_payment_mode_id(self, record):
        if record.get("f_pago") and record.get("f_pago") in ["1", "2"]:
            payment_mode = self.env["account.payment.mode"].search(
                [("prestashop_name", "=", record.get("f_pago"))]
            )
            if not payment_mode:
                raise MappingError(
                    _("Payment mode with {} prestashop name not found.").format(
                        record.get("f_pago")
                    )
                )
            return {"customer_payment_mode_id": payment_mode.id}
        return {}

    @mapping
    def payment_days(self, record):
        if record.get("dias") and record.get("dias") not in ["0", ""]:
            payment_days = int(record.get("dias"))
            return {"payment_days": payment_days}

    @mapping
    def sale_team(self, record):
        if record.get("odoo_shop_id"):
            crm_team = self.env["crm.team"].search(
                [("prestashop_id", "=", record.get("odoo_shop_id"))]
            )
            if not crm_team:
                raise MappingError(
                    _("CRM team with {} prestashop id not found.").format(
                        record.get("plazo")
                    )
                )
            return {"team_id": crm_team.id}

    @mapping
    def name(self, record):
        name = None
        adapter = self.component(usage='backend.adapter', model_name='prestashop.address')
        address_ids = adapter.search(filters={'filter[id_customer]': '%d' % (int(record['id']),)})
        for address_id in address_ids:
            address = adapter.read(address_id)
            if address.get('facturacion_defecto') == '1':
                if address['company']:
                    name = address['company']
                else:
                    parts = [address['firstname'], address['lastname']]
                    name = ' '.join(p.strip() for p in parts if p.strip())
        if not name:
            parts = [record['firstname'], record['lastname']]
            name = ' '.join(p.strip() for p in parts if p.strip())
        return {'name': name}


class AddressImportMapper(Component):
    _inherit = "prestashop.address.mappper"

    @only_create
    @mapping
    def type(self, record):
        # do not set 'contact', otherwise the address fields are shared with
        # the parent
        if (
            record.get("facturacion_defecto") == "1"
            and record.get("envio_defecto") == "1"
        ):
            return {}
        if record.get("envio_defecto") == "1":
            return {"type": "delivery"}
        elif record.get("facturacion_defecto") == "1":
            return {"type": "invoice"}
        return {"type": "other"}

    @only_create
    @mapping
    def parent_id(self, record):
        binder = self.binder_for("prestashop.res.partner")
        parent = binder.to_internal(record["id_customer"], unwrap=True)
        if (
            record.get("facturacion_defecto") == "1"
            and record.get("envio_defecto") == "1"
            and not parent.prestashop_address_bind_ids
        ):
            return {}
        return super().parent_id(record)

    @only_create
    @mapping
    def odoo_id(self, record):
        if (
            record.get("facturacion_defecto") == "1"
            and record.get("envio_defecto") == "1"
        ):
            binder = self.binder_for("prestashop.res.partner")
            parent = binder.to_internal(record["id_customer"], unwrap=True)
            if not parent.prestashop_address_bind_ids:
                return {"odoo_id": parent.id}

    @mapping
    def name(self, record):
        name = ''
        if record.get('facturacion_defecto') == '1':
            if record['company']:
                name = record['company']
        if not name:
            parts = [record['firstname'], record['lastname']]
            name = ' '.join(p.strip() for p in parts if p.strip())
        return {'name': name}


class AddressImporter(Component):
    _inherit = 'prestashop.address.importer'

    def _after_import(self, binding):
        record = self.prestashop_record
        vat_number = None
        if record.get("facturacion_defecto") == "1":
            sii_simplified = True
            if binding.odoo_id.country_id in (self.env.ref('base.es'), self.env.ref('base.pt')):
                sii_simplified = False
            if record['vat_number']:
                vat_number = record['vat_number'].replace('.', '').replace(' ', '')
            # TODO move to custom localization module
            elif not record['vat_number'] and record.get('dni'):
                vat_number = record['dni'].replace('.', '').replace(
                    ' ', '').replace('-', '')
            if vat_number:
                if vat_number[:2] != binding.odoo_id.country_id.code:
                    vat_number = binding.odoo_id.country_id.code + vat_number
                if self._check_vat(vat_number, binding.odoo_id.country_id):
                    sii_simplified = False
                else:
                    msg = _('Please, check the VAT number: %s') % vat_number
                    self.backend_record.add_checkpoint(
                        binding.parent_id or binding,
                        message=msg,
                    )
                    vat_number = None
            if sii_simplified:
                    if binding.parent_id:
                        binding.parent_id.write({'vat': vat_number, 'sii_simplified_invoice': sii_simplified})
                    else:
                        binding.write({'vat': vat_number, 'sii_simplified_invoice': sii_simplified})
