# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.addons.component.core import Component


class AccountPaymentMode(models.Model):

    _inherit = "account.payment.mode"

    prestashop_name = fields.Char()
    prestashop_module = fields.Char()
    can_edit = fields.Boolean()
    check_risk = fields.Boolean()
    defaullt_sale_invoice_policy = fields.Selection(
        [("order", "Ordered quantities"), ("delivery", "Delivered quantities")]
    )


class PaymentModeBinder(Component):
    _inherit = "account.payment.mode.binder"
    _external_field = "prestashop_module"

    def to_internal(self, external_id, unwrap=False, company=None):
        if company is None:
            company = self.backend_record.company_id
        bindings = self.model
        for language in self.backend_record.language_ids:
            new_bindings = self.model.with_context(
                active_test=False, lang=language.code
            ).search(
                [
                    (self._external_field, "ilike", external_id),
                    ("company_id", "=", company.id),
                ]
            )
            bindings |= new_bindings.filtered(
                lambda r: external_id in r.prestashop_module.split(",")
            )
        if not bindings:
            return self.model.browse()
        bindings.ensure_one()
        return bindings
