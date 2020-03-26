# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class StockLocation(models.Model):
    _inherit = "stock.location"

    oldname = fields.Char("Importado como")
