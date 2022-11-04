# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Volumetry A-SEC",
    "summary": "Customization over warehouse. Volumetry",
    "version": "12.0.1.0.0",
    "author": "Comunitea",
    "category": "Inventory",
    "depends": [
        "stock",
        "stock_picking_batch_extended",
    ],
    "data": [
        "views/stock_location.xml",
        "views/product.xml",
        "views/stock_picking.xml",
        "views/stock_picking_batch.xml",
    ],
    "installable": True,
    "license": "AGPL-3",
}
