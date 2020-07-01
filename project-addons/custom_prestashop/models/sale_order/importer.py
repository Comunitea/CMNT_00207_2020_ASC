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
            partner_id = record["id_customer"]

            partner_adapter = self.component(
                usage="backend.adapter", model_name="prestashop.res.partner"
            )
            partner_data = partner_adapter.read(partner_id)
            if partner_data.get("f_pago") and partner_data.get("f_pago") in [
                "1",
                "2",
            ]:
                payment_mode = self.env["account.payment.mode"].search(
                    [("prestashop_name", "=", partner_data.get("f_pago"))]
                )
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
    def fiscal_position_id(self, record):
        order_lines = (
            record.get("associations").get("order_rows").get("order_row")
        )
        if isinstance(order_lines, dict):
            order_lines = [order_lines]
        line_taxes = []
        sale_line_adapter = self.component(
            usage="backend.adapter", model_name="prestashop.sale.order.line"
        )
        for line in order_lines:
            line_data = sale_line_adapter.read(line["id"])
            prestashop_tax_id = (
                line_data.get("associations").get("taxes").get("tax").get("id")
            )
            if prestashop_tax_id not in line_taxes:
                line_taxes.append(prestashop_tax_id)

        fiscal_positions = self.env["account.fiscal.position"]
        for tax_id in line_taxes:
            matched_fiscal_position = self.env[
                "account.fiscal.position"
            ].search([("prestashop_tax_ids", "ilike", tax_id)])
            fiscal_positions += matched_fiscal_position.filtered(
                lambda r: tax_id in r.prestashop_tax_ids.split(",")
            )
        if len(fiscal_positions) > 1:
            if record.get('associations').get('recargos_equivalencia').get('recargo_equivalencia'):
                preferred_fiscal_positions = fiscal_positions.filtered(lambda r: r.recargo_equivalencia
                )
            else:
                preferred_fiscal_positions = fiscal_positions.filtered(lambda r: not  r.recargo_equivalencia
                )
            if preferred_fiscal_positions:
                fiscal_positions = preferred_fiscal_positions
        if len(fiscal_positions) != 1:
            raise Exception(
                "Error al importar posicion fiscal para los impuestos {}".format(
                    line_taxes
                )
            )
        return {"fiscal_position_id": fiscal_positions.id}

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

    @mapping
    def commission_amount(self, record):
        commission_amount = (
            record.get("associations", {})
            .get("payment_commissions", {})
            .get("payment_commission", {})
            .get("commission")
        )
        if commission_amount:
            if self.backend_record.taxes_included:
                return {"commission_amount": float(commission_amount)}
            else:
                fpos_id = self.fiscal_position_id(record)["fiscal_position_id"]
                fpos = self.env["account.fiscal.position"].browse(fpos_id)
                tax = (
                    fpos.map_tax(
                        self.backend_record.discount_product_id.taxes_id
                    )
                    if fpos
                    else self.backend_record.discount_product_id.taxes_id
                )
                factor_tax = not tax.price_include and (1 + tax.amount / 100) or 1.0
                return {
                    "commission_amount": float(commission_amount) / factor_tax
                }
        return {}

    @mapping
    def notes(self, record):
        messages = (
            record.get("associations").get("messages").get("message")
        )
        if isinstance(messages, dict):
            messages = [messages]
        if messages:
            return {'note': '\n'.join([x.get('message') for x in messages if x['private'] == '0'])}

    def _map_child(self, map_record, from_attr, to_attr, model_name):
        binder = self.binder_for("prestashop.sale.order")
        source = map_record.source
        if callable(from_attr):
            child_records = from_attr(self, source)
        else:
            child_records = source[from_attr]
        exists = binder.to_internal(source["id"])
        current_lines = []
        remove_lines = []
        if exists:
            incoming_lines = [int(x["id"]) for x in child_records]
            if model_name == "prestashop.sale.order.line":
                current_lines = [
                    x.prestashop_id for x in exists.prestashop_order_line_ids
                ]
            else:
                current_lines = [
                    x.prestashop_id for x in exists.prestashop_discount_line_ids
                ]
            remove_lines = list(set(current_lines) - set(incoming_lines))
        context = dict(self.env.context)
        context["model_name"] = model_name
        self.env.context = context
        res = super()._map_child(map_record, from_attr, to_attr, model_name)
        if remove_lines:
            for line in remove_lines:
                res.append((2, line))
        return res


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
                self.env.context["model_name"]
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
        if self._get_binding():
            ps_state_id = self.prestashop_record["current_state"]
            state = self.binder_for("prestashop.sale.order.state").to_internal(
                ps_state_id, unwrap=1
            )
            self._get_binding().prestashop_state = state.id
        if self._get_binding().prestashop_state.trigger_cancel:
            return True
        rules = self.component(usage="sale.import.rule")
        if (
            self._get_binding()
            and not self._get_binding().payment_mode_id.can_edit
            and not self._get_binding().ready_to_send
        ):
            return True
        try:
            return rules.check(self.prestashop_record)
        except NothingToDoJob as err:
            # we don't let the NothingToDoJob exception let go out, because if
            # we are in a cascaded import, it would stop the whole
            # synchronization and set the whole job to done
            return str(err)

    def _after_import(self, binding):
        res = super()._after_import(binding)
        if binding.commission_amount:
            discount_product = self.backend_record.discount_product_id
            added_amount = False
            for line in binding.odoo_id.order_line:
                if line.product_id.id == discount_product.id:
                    # Ya tiene un descuento, sumamos la cantidad
                    added_amount = True
                    if (
                        line.applied_commission_amount
                        and line.applied_commission_amount
                        != binding.commission_amount
                    ):
                        line.price_unit = (
                            line.price_unit
                            - line.applied_commission_amount
                            + binding.commission_amount
                        )
                        line.applied_commission_amount = (
                            binding.commission_amount
                        )
                    if not line.applied_commission_amount:
                        line.price_unit += binding.commission_amount
                        line.applied_commission_amount = (
                            binding.commission_amount
                        )
                    break
            if not added_amount:
                taxes = discount_product.taxes_id
                taxes_ids = taxes.ids
                if binding.partner_id and binding.fiscal_position_id:
                    taxes_ids = binding.fiscal_position_id.map_tax(
                        taxes, discount_product, binding.partner_id
                    ).ids
                binding.odoo_id.write(
                    {
                        "order_line": [
                            (
                                0,
                                0,
                                {
                                    "commission_amount": binding.commission_amount,
                                    "product_id": discount_product.id,
                                    "name": discount_product.name,
                                    "price_unit": binding.commission_amount,
                                    "applied_commission_amount": binding.commission_amount,
                                    "tax_id": [(6, 0, taxes_ids)],
                                },
                            )
                        ]
                    }
                )
        return res
