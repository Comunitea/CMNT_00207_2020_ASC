# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Product Report Custom",
    "summary": "Product report custom",
    "version": "12.0.1.0.0",
    "author": "Comunitea",
    "category": "Sales",
    "depends": ["sale"],
    "data": [
        "views/product_product.xml",
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "license": "AGPL-3",
}
