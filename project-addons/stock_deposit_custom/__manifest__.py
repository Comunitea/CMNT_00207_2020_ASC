# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Stock deposit custom',
    'version': '12.0',
    'category': 'stock',
    'description': """Manage deposit of goods""",
    'author': 'Comunitea Servicios Tecnológicos, S.L.',
    'website': 'www.comunitea.com',
    'depends': ['sale_stock'],
    'data': ['views/sale_view.xml',
             'views/res_partner_view.xml',
             'views/stock.xml',
             'data/stock_deposit_data.xml',
              ],
    'installable': True
}
