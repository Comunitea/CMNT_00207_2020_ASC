# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SaleOrderState(models.Model):

    _inherit = "sale.order.state"

    trigger_paid = fields.Boolean()
    trigger_cancel = fields.Boolean()
