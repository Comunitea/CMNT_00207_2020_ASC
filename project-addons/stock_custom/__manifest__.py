# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Custom A-SEC",
    "summary": "Customization over warehouse",
    "version": "12.0.1.0.0",
    "author": "Comunitea",
    "category": "Inventory",

    "depends": ["stock",
                "product",
                "stock_removal_location_by_priority",
                "stock_picking_report_valued",
                "stock_picking_type_group", "warehouse_apk"],
    "data": [
        'security/ir.model.access.csv',
        'data/cron.xml',
        "views/stock_location.xml",
        "views/product_view.xml",
        'views/stock_picking.xml',
        'views/sale_order.xml',
        'views/variable_replensih.xml',
        'views/stock_production_lot.xml',
    ],
    "installable": True,
    "license": "AGPL-3",
}
