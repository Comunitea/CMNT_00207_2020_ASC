# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields


class RmaOrderLine(models.Model):

    _inherit = 'rma.order.line'

    team_id = fields.Many2one(related='invoice_id.team_id')