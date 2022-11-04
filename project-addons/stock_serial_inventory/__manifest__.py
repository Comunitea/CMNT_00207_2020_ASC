# © 2018 Comunitea - Kiko Sánchez <kiko@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Serial Inventory For Alternative Tracking",
    "version": "12.0.0.0.0",
    "category": "Warehouse",
    "license": "AGPL-3",
    "author": "Comunitea, ",
    "depends": [
       "alternative_tracking",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_serial_inventory_views.xml",
        "wizard/serial_mngm_wzd.xml"
    ],
    "installable": True,
}
