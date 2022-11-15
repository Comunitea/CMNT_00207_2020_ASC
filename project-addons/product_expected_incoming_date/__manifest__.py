# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Product Expected Incoming Date",
    "summary": "Field for expected data with stock. Check first incoming movement",
    "version": "12.0.1.0.0",
    "author": "Comunitea",
    "category": "stock",
    "depends": ["stock"],
    "data": [
        "views/product_product.xml",
        "views/product_qty_state.xml",
        "views/stock.xml",
        "wizard/wzd_incoming_product.xml",
        "security/ir.model.access.csv"
    ],
    "installable": True,
    "license": "AGPL-3",
}
