# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class Picking(models.Model):
    _inherit = 'stock.picking'

    mail_sended = fields.Boolean()
    team_id = fields.Many2one(related='sale_id.team_id')
    scheduled_date_report = fields.Date(compute='_compute_scheduled_date_report')

    def _compute_scheduled_date_report(self):
        for pick in self:
            pick.scheduled_date_report = pick.scheduled_date.date()
