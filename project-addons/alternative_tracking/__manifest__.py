# © 2018 Comunitea - Kiko Sánchez <kiko@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Alternative Tracking",
    "version": "12.0.0.0.0",
    "category": "Product",
    "license": "AGPL-3",
    "author": "Comunitea, ",
    "depends": [
        "mrp",
        "stock",
        "stock_account",
        "web_widget_color",
        "stock_picking_batch_extended",
        "forbidden_lot_names"
    ],
    "data": [
        "security/ir.model.access.csv",
        
        "views/stock_move.xml",
        "views/stock_picking.xml",
        "views/stock_picking_batch.xml",
        "views/stock_production_lot.xml",
        "views/product_views.xml",
        "views/stock_location.xml",
        
        
    ],
    "installable": True,
}
