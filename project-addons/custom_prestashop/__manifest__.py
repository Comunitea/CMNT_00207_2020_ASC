# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Prestashop customizations",
    "version": "12.0.1.0.0",
    "category": "Connector",
    "author": "Comunitea",
    "maintainer": "Comunitea",
    "website": "www.comunitea.com",
    "license": "AGPL-3",
    "depends": [
        "connector_prestashop",
        "cmnt_prestashop_custom",
        "sales_team",
        "base_multi_image",
        "base_location",
        "stock_custom",
        "sale_financial_risk"
    ],
    "data": [
        "views/account_payment_term.xml",
        "views/crm_team.xml",
        "views/account_payment_mode.xml",
        "views/product_attribute.xml",
        "views/prestashop_backend.xml",
        "views/sale_order_state.xml",
        "views/account_fiscal_position.xml",
        "data/sale_exception.xml",
        "wizard/prestashop_import_customer_wizard.xml",
    ],
}
