# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Custom A-SEC",
    "summary": "Customization over warehouse",
    "version": "12.0.1.0.0",
    "author": "Comunitea",
    "category": "Inventory",

    "depends": ["stock",
                "stock_removal_location_by_priority",
                "stock_picking_report_valued"],
    "data": [
        "views/stock_location.xml",
        'views/stock_picking.xml'
    ],
    "installable": True,
    "license": "AGPL-3",
}
