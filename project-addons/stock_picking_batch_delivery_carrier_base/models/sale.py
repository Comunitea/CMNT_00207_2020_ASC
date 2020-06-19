# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    needs_signature = fields.Boolean(
        related="carrier_id.needs_signature", readonly=True, store=True
    )
