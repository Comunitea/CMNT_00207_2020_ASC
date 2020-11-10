# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def _get_fiscal_position(self):
        self.ensure_one()
        fiscal_position = (
            self.fiscal_position_id or self.partner_id.property_account_position_id
        )
        if fiscal_position and self.team_id.invoice_on_company:
            crm_company = self.team_id.invoice_on_company
            if self.fiscal_position_id:
                fpos_xml_id = self.fiscal_position_id._get_external_ids()[
                    self.fiscal_position_id.id
                ][0]
                new_fpos_xml_id = fpos_xml_id.replace(
                    "{}_".format(self.fiscal_position_id.company_id.id),
                    "{}_".format(self.team_id.invoice_on_company.id),
                )
                fiscal_position = self.sudo().env.ref(new_fpos_xml_id)
            else:
                fiscal_position = (
                    self.partner_invoice_id.with_context(
                        force_company=crm_company.id
                    ).property_account_position_id,
                )
        return fiscal_position

    @api.multi
    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.team_id.invoice_on_company:
            crm_company = self.team_id.invoice_on_company
            res["company_id"] = crm_company.id
            journal_id = (
                self.sudo()
                .env["account.invoice"]
                .with_context(company_id=crm_company.id)
                .default_get(["journal_id"])["journal_id"]
            )
            if not journal_id:
                raise UserError(
                    _("Please define an accounting sales journal for this company.")
                )
            res["journal_id"] = journal_id
            res["account_id"] = (
                self.partner_invoice_id.with_context(
                    force_company=crm_company.id
                ).property_account_receivable_id.id,
            )
            new_fpos = self._get_fiscal_position()
            if new_fpos:
                res["fiscal_position_id"] = new_fpos.id
            if res.get("payment_mode_id"):
                old_payment_mode = self.env["account.payment.mode"].browse(
                    res.get("payment_mode_id")
                )
                old_payment_mode_xml_id = old_payment_mode._get_external_ids()[
                    old_payment_mode.id
                ][0]
                new_payment_mode_xml_id = old_payment_mode_xml_id.replace(
                    "{}_".format(old_payment_mode.company_id.id),
                    "{}_".format(crm_company.id),
                )
                new_payment_mode = self.sudo().env.ref(new_payment_mode_xml_id)
                res["payment_mode_id"] = new_payment_mode.id
            res.pop("payment_term_id")
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super()._prepare_invoice_line(qty)
        if self.order_id.team_id.invoice_on_company:
            crm_company = self.order_id.team_id.invoice_on_company
            product = self.product_id.with_context(force_company=crm_company.id)
            account = (
                product.property_account_income_id
                or product.categ_id.property_account_income_categ_id
            )
            if not account and self.product_id:
                raise UserError(
                    _(
                        'Please define income account for this product: "%s" (id:%d) - or for its category: "%s".'
                    )
                    % (
                        self.product_id.name,
                        self.product_id.id,
                        self.product_id.categ_id.name,
                    )
                )
            fpos = self.order_id._get_fiscal_position()
            if fpos and account:
                account = fpos.map_account(account)
            res["account_id"] = account.id
            res.pop("account_analytic_id")
            taxes = []
            for tax_id in res["invoice_line_tax_ids"][0][2]:
                old_tax = self.env["account.tax"].browse(tax_id)
                old_tax_xml_id = old_tax._get_external_ids()[old_tax.id][0]
                new_tax_xml_id = old_tax_xml_id.replace(
                    "{}_".format(old_tax.company_id.id),
                    "{}_".format(self.order_id.team_id.invoice_on_company.id),
                )
                new_tax = self.sudo().env.ref(new_tax_xml_id)
                taxes.append(new_tax.id)
            res["invoice_line_tax_ids"] = [(6, 0, taxes)]
        return res
