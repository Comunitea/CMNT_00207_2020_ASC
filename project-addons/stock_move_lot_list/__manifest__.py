# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Move Serial List",
    "summary": "Module to import/load/read seeveral seial numbers for stock move",
    "version": "12.0.1.0.0",
    "author": "Comunitea",
    "category": "Inventory",
    "depends": ["stock"],
    "data": [
        "views/stock_move.xml",
        "views/stock_picking_type.xml",
        "views/stock_location.xml",
        "wizards/create_lot_wzd.xml"
    ],
    "installable": True,
    "license": "AGPL-3",
}
