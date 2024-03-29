##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2020 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
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
    "name": "Stock Picking Batch Delivery Carrier Base",
    "version": "12.0.0.0.0",
    "summary": "Base Module for stock picking batch deliveries",
    "category": "Custom",
    "author": "comunitea",
    "website": "www.comunitea.com",
    "license": "AGPL-3",
    "depends": [
        "sale_shipping_info_helper",
        "delivery",
        "custom_prestashop",
        "cmnt_delivery_carrier_label",
        "account_payment_mode",
        "stock_custom"
    ],
    "data": [
        "wizard/picking_sign_wizard.xml",
        "views/stock_picking_batch.xml",
        "views/account_payment_mode.xml",
        "views/sale.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
