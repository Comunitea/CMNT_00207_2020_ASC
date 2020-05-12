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

    @mapping
    def parent_id(self, record):
        if (
            record.get("facturacion_defecto") == "1"
            and record.get("envio_defecto") == "1"
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
            return {"odoo_id": parent.id}


# class AddressImporter(Component):
#     _inherit = "prestashop.address.importer"

#     def _after_import(self, binding):
#         record = self.prestashop_record
#         vat_number = None
#         if record["vat_number"]:
#             vat_number = record["vat_number"].replace(".", "").replace(" ", "")
#         # TODO move to custom localization module
#         elif not record["vat_number"] and record.get("dni"):
#             vat_number = (
#                 record["dni"].replace(".", "").replace(" ", "").replace("-", "")
#             )
#         write_binding = binding.parent_id or binding
#         if vat_number:
#             if self._check_vat(vat_number, write_binding.country_id):
#                 write_binding.write({"vat": vat_number})
#             else:
#                 msg = _("Please, check the VAT number: %s") % vat_number
#                 self.backend_record.add_checkpoint(write_binding, message=msg)

#     def _check_vat(self, vat_number, partner_country):
#         if self.env.context.get("company_id"):
#             company = self.env["res.company"].browse(
#                 self.env.context["company_id"]
#             )
#         else:
#             company = self.env.user.company_id
#         if company.vat_check_vies:
#             # force full VIES online check
#             check_func = self.env["res.partner"].vies_vat_check
#         else:
#             # quick and partial off-line checksum validation
#             check_func = self.env["res.partner"].simple_vat_check
#         # check with country code as prefix of the TIN
#         vat_country, vat_number_ = self.env["res.partner"]._split_vat(
#             vat_number
#         )
#         if not check_func(vat_country, vat_number_):
#             # if fails, check with country code from country
#             country_code = partner_country.code
#             if country_code:
#                 if not check_func(country_code.lower(), vat_number):
#                     return False
#         return True
