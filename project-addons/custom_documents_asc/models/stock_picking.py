# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class Picking(models.Model):
    _inherit = 'stock.picking'

    mail_sended = fields.Boolean()
    team_id = fields.Many2one('crm.team')
    scheduled_date_report = fields.Date(compute='_compute_scheduled_date_report')

    def _compute_scheduled_date_report(self):
        for pick in self:
            pick.scheduled_date_report = pick.scheduled_date.date()

    @api.model
    def create(self, vals):
        if 'team_id' not in vals:
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            if partner:
                vals['team_id'] = partner.commercial_partner_id.team_id.id
        return super().create(vals)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        team_id = self.sale_line_id.order_id.team_id
        if team_id:
            vals['team_id'] = team_id.id
        return vals
