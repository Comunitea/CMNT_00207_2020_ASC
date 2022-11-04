##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2019 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
#    Vicente Ángel Gutiérrez <vicente@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Apk Manager",
    "version": "12.0.1.0",
    "summary": "APK ASEC V3",
    "category": "Custom",
    "author": "comunitea",
    "website": "www.comunitea.com",
    "license": "AGPL-3",
    "depends": [
        "sale_stock",
        "delivery",
        "stock_picking_batch_extended",
        "stock_custom",
        "alternative_tracking",
        "stock_removal_location_by_priority",
        "stock_serial_inventory",
        "forbidden_lot_names"


    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking_type.xml",
        "views/stock_location.xml",
        "views/product_uom.xml",
        "views/crm_team.xml",
        "views/carrier.xml",
        "views/product_uom.xml",
        # "views/move_line_grouped.xml",
        "views/stock_picking_batch.xml",
       "views/stock_move_line.xml", 
        "wizard/stock_picking_to_pda_views.xml",
        

    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
