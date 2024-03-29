# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component


class PrestashopModelBinder(Component):
    _inherit = "prestashop.binder"

    _apply_on = [
        "prestashop.shop.group",
        "prestashop.shop",
        "prestashop.res.partner",
        "prestashop.address",
        "prestashop.res.partner.category",
        "prestashop.res.lang",
        "prestashop.res.country",
        "prestashop.res.currency",
        "prestashop.account.tax",
        "prestashop.account.tax.group",
        "prestashop.product.category",
        "prestashop.product.image",
        "prestashop.product.template",
        "prestashop.product.combination",
        "prestashop.product.combination.option",
        "prestashop.product.combination.option.value",
        "prestashop.sale.order",
        "prestashop.sale.order.line",
        "prestashop.sale.order.line.discount",
        "prestashop.sale.order.state",
        "prestashop.delivery.carrier",
        "prestashop.refund",
        "prestashop.supplier",
        "prestashop.product.supplierinfo",
        "prestashop.mail.message",
        "prestashop.groups.pricelist",
        "prestashop.product.brand"
    ]
