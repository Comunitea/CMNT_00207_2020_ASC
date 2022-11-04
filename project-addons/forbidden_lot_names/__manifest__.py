# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Forbidden Lot/serial Names Custom A-SEC",
    "summary": "Avoid barcodes/default_code as lot names for product",
    "version": "12.0.1.0.0",
    "author": "Comunitea",
    "category": "Inventory",
    "depends": [
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_view.xml",
    ],
    "installable": True,
    "license": "AGPL-3",
}
