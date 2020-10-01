# Copyright 2020 Comunitea
# @author KIko Sánchez <kiko@comunitea.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{
    'name': 'Carrier Report XLS',
    'version': '12.0.0.0.0',
    'category': 'Tools',
    'license': 'AGPL-3',
    'summary': 'Generate XLSX reports for delivery',
    'description': """
    """,
    'author': "Comunitea",
    'website': 'http://www.comunitea.com',
    'depends': ['cmnt_delivery_carrier_label', 'stock_picking_batch_delivery_carrier_base'],
    'data': [
        'wizard/carrier_report_xlsx.xml',
        ],
    'installable': True,
}
