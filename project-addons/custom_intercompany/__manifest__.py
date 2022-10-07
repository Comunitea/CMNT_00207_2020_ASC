# Copyright 2020 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Intercompany WZD",
    "version": "12.0.0.0.0",
    "category": "account",
    "description": """Customizations for improving the mangament of
    intercompany flows""",
    "author": "Comunitea",
    "website": "https://www.comunitea.com",
    "depends": [
        # "product_tax_multicompany_default",
        # "picking_incidences",
        "account",
        "account_invoice_inter_company",
        "custom_account",

    ],
    "data": [
        "views/account_invoice.xml",
        "views/crm_team.xml",
        "wizard/wzd_intercomp_invoice_view.xml",
    ],
    "installable": True,
}


