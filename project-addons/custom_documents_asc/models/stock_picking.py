# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _

class Picking(models.Model):
    _inherit = 'stock.picking'

    team_id = fields.Many2one(related='sale_id.team_id')