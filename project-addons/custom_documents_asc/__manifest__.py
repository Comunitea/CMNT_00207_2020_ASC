# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Documents customizations for A-sec',
    'version': '12.0.1.0.0',
    'summary': '',
    'category': 'custom',
    'author': 'Comunitea',
    'maintainer': 'Comunitea',
    'website': 'www.comunitea.com',
    'license': 'AGPL-3',
    'depends': [
        'web',
        'sale_stock',
        'purchase',
        'rma_sale',
    ],
    'data': [
        'views/report_templates.xml',
        'views/crm_team.xml',
        'views/rma_report_templates.xml',
        'views/purchase_order_templates.xml',
        'views/report_invoice.xml',
        'views/stock_picking_report_valued.xml'
    ],    
}