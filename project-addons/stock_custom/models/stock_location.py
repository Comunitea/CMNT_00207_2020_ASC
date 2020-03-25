# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

from odoo import api, models, fields, _

class StockLocation(models.Model):
    _inherit = 'stock.location'

    oldname = fields.Char('Importado como')
