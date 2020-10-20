# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Production LOt Duplicate Advice",
    "summary": "Check duplciate lots",
    "version": "12.0.1.0.0",
    "author": "Comunitea",
    "category": "Inventory",
    "depends": [
        "stock",
    ],
    "data": [
        "views/stock_production_lot.xml",
        "data/cron.xml",
    ],
    "installable": True,
    "license": "AGPL-3",
}
