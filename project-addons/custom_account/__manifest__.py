# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account customizations",
    "version": "12.0.1.0.0",
    "summary": "",
    "category": "Accounting",
    "author": "Comunitea",
    "maintainer": "Comunitea",
    "website": "www.comunitea.com",
    "license": "AGPL-3",
    "depends": [
        "account",
        "sale",
        "sales_team",
        "l10n_es_mis_report",
        "l10n_es_account_invoice_sequence",
        "l10n_es_aeat_sii",
        "base_automation",
        "account_reconcile_payment_order",
        "account_asset_management",
        "purchase_landed_cost"
    ],
    "data": [
        "data/custom_account_data.xml",
        "views/account_move_view.xml",
        "views/account_payment_mode.xml",
        "views/account_invoice.xml",
        "views/crm_team.xml",
        "security/ir.model.access.csv"
    ],
}
