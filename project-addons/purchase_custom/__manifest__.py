# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Purchase custom",
    "version": "12.0",
    "category": "stock",
    "description": """Purchase customizations""",
    "author": "Comunitea Servicios Tecnológicos, S.L.",
    "website": "www.comunitea.com",
    "depends": ["purchase", "sale", "product_brand", "quant_picking_rel"],
    "data": [
        "data/data.xml",
        "views/purchase_order.xml",
        "report/purchase_report.xml"
    ],
    "installable": True,
}
