# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    prestashop_tax_ids = fields.Char(help="comma separated ids of prestashop taxes"
    )
    preferred_for_backend_ids = fields.Many2many('prestashop.backend')
