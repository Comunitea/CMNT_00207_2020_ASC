# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import FailedJobError

MODO_DIFERIDO = '_sd_pago_rapido'


class SaleImportRule(Component):
    _inherit = "prestashop.sale.import.rule"

    def check(self, record):
        """ Check whether the current sale order should be imported
        or not. It will actually use the payment mode configuration
        and see if the chosen rule is fullfilled.

        :returns: True if the sale order should be imported
        :rtype: boolean
        """
        ps_payment_method = record["module"]
        mode_binder = self.binder_for("account.payment.mode")
        if ps_payment_method == MODO_DIFERIDO:
            partner = record["id_customer"]
            partner_binder = self.binder_for("prestashop.res.partner")
            payment_mode = partner_binder.to_internal(
                partner, unwrap=True
            ).customer_payment_mode_id
            if not payment_mode:
                payment_mode = mode_binder.to_internal(ps_payment_method)
        else:
            payment_mode = mode_binder.to_internal(ps_payment_method)
        if not payment_mode:
            raise FailedJobError(
                _(
                    "The configuration is missing for the Payment Mode '%s'.\n\n"
                    "Resolution:\n"
                    " - Use the automatic import in 'Connectors > PrestaShop "
                    "Backends', button 'Import payment modes', or:\n"
                    "\n"
                    "- Go to 'Invoicing > Configuration > Management "
                    "> Payment Modes'\n"
                    "- Create a new Payment Mode with name '%s'\n"
                    "-Eventually  link the Payment Method to an existing Workflow "
                    "Process or create a new one."
                )
                % (ps_payment_method, ps_payment_method)
            )
        self._rule_global(record, payment_mode)
        self._rule_state(record, payment_mode)
        self._rules[payment_mode.import_rule](self, record, payment_mode)


class SaleOrderImportMapper(Component):
    _inherit = "prestashop.sale.order.mapper"

    @mapping
    def payment(self, record):
        ps_payment_method = record["module"]
        if ps_payment_method == MODO_DIFERIDO:
            partner = record["id_customer"]
            partner_binder = self.binder_for("prestashop.res.partner")
            payment_mode = partner_binder.to_internal(
                partner, unwrap=True
            ).customer_payment_mode_id
            if not payment_mode:
                raise Exception('Payment mode not configured in partner')
        else:
            binder = self.binder_for("account.payment.mode")
            payment_mode = binder.to_internal(record["module"])
        assert payment_mode, (
            "import of error fail in SaleImportRule.check "
            "when the payment mode is missing"
        )
        return {"payment_mode_id": payment_mode.id}

