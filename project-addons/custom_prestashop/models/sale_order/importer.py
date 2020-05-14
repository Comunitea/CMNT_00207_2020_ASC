# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import FailedJobError, NothingToDoJob

MODO_DIFERIDO = "_sd_pago_rapido"


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
    _map_child_fallback = "sale.order.line.map.child.import"

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
                raise Exception("Payment mode not configured in partner")
        else:
            binder = self.binder_for("account.payment.mode")
            payment_mode = binder.to_internal(record["module"])
        assert payment_mode, (
            "import of error fail in SaleImportRule.check "
            "when the payment mode is missing"
        )
        return {"payment_mode_id": payment_mode.id}

    @mapping
    @only_create
    def name(self, record):
        basename = record["reference"]
        if not self._sale_order_exists(basename):
            return {"name": basename}
        i = 1
        name = basename + "_%d" % (i)
        while self._sale_order_exists(name):
            i += 1
            name = basename + "_%d" % (i)
        return {"name": name}


class ImportMapChild(Component):
    _name = "sale.order.line.map.child.import"
    _inherit = "base.map.child.import"

    def format_items(self, items_values):
        """ Format the values of the items mapped from the child Mappers.

        It can be overridden for instance to add the Odoo
        relationships commands ``(6, 0, [IDs])``, ...

        As instance, it can be modified to handle update of existing
        items: check if an 'id' has been defined by
        :py:meth:`get_item_values` then use the ``(1, ID, {values}``)
        command

        :param items_values: list of values for the items to create
        :type items_values: list

        """
        res = []
        for values in items_values:
            if "tax_id" in values:
                values.pop("tax_id")
            prestashop_id = values["prestashop_id"]
            prestashop_binding = self.binder_for(
                "prestashop.sale.order.line"
            ).to_internal(prestashop_id)
            if prestashop_binding:
                values.pop("prestashop_id")
                final_vals = {}
                for item in values.keys():
                    # integer and float values come as string
                    if (
                        prestashop_binding._fields[item].type == "integer"
                        and values[item]
                    ):
                        if int(values[item]) != prestashop_binding[item]:
                            final_vals[item] = values[item]
                    elif (
                        prestashop_binding._fields[item].type == "float"
                        and values[item]
                    ):
                        if float(values[item]) != prestashop_binding[item] and (
                            prestashop_binding[item] - float(values[item])
                            > 0.01
                            or prestashop_binding[item] - float(values[item])
                            < -0.01
                        ):
                            final_vals[item] = values[item]
                    elif prestashop_binding._fields[item].type == "many2one":
                        if values[item] != prestashop_binding[item].id:
                            final_vals[item] = values[item]
                    else:
                        if values[item] != prestashop_binding[item]:
                            final_vals[item] = values[item]
                if final_vals:
                    res.append((1, prestashop_binding.id, final_vals))
            else:
                res.append((0, 0, values))
        return res


class SaleOrderImporter(Component):
    _inherit = "prestashop.sale.order.importer"

    def _has_to_skip(self):
        """ Sobreescribimos para traernos cualquier actualización sobre el pedido """
        rules = self.component(usage="sale.import.rule")
        try:
            return rules.check(self.prestashop_record)
        except NothingToDoJob as err:
            # we don't let the NothingToDoJob exception let go out, because if
            # we are in a cascaded import, it would stop the whole
            # synchronization and set the whole job to done
            return str(err)
