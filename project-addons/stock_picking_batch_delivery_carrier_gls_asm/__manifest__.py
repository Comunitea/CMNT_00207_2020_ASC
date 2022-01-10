##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2021 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
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
    "name": "Stock Picking Batch GLS ASM Express Connector",
    "version": "12.0.0.0.0",
    "summary": "GLS ASM Express API integration for Stock Picking Batches",
    "category": "Custom",
    "author": "comunitea",
    "website": "www.comunitea.com",
    "license": "AGPL-3",
    "depends": [
        "stock_picking_batch_delivery_carrier_base",
    ],
    "external_dependencies" : {
        "python" : ["suds"],
    },
    "data": [
        "data/delivery_asm_data.xml",
        "data/mail_data.xml",
        "views/delivery_asm_view.xml",
        "views/gls_asm_manifest_template.xml",
        "wizard/gls_asm_manifest_wizard_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
