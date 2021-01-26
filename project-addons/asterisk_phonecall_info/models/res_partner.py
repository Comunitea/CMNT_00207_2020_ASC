# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _, fields
from datetime import date


class ResPartner(models.Model):
    _inherit = "res.partner"

    commercial_minutes = fields.Float(string="Total commercial minutes", compute="_compute_phonecall_minutes")
    technical_minutes = fields.Float(string="Total technical minutes", compute="_compute_phonecall_minutes")
    commercial_minutes_cur_month = fields.Float(string="Commercial minutes this month", compute="_compute_phonecall_minutes")
    technical_minutes_cur_month = fields.Float(string="Technical minutes this month", compute="_compute_phonecall_minutes")

    @api.multi
    def _compute_phonecall_minutes(self):
        for partner in self:
            cur_month = date.today().strftime('%B').lower()
            cur_year = date.today().year
            cur_date = "{} {}".format(cur_month, cur_year)
            
            commercial_calls = self.env['crm.phonecall'].read_group([
                ('partner_id', '=', partner.id),
                ('asterisk_user_type', '=', 'commercial')
            ], fields=['length', 'date'], groupby=['date'])

            partner.commercial_minutes = sum(call['length'] for call in commercial_calls)/60
            partner.commercial_minutes_cur_month = sum(call['length'] for call in commercial_calls if call['date'] == cur_date)/60

            technical_calls = self.env['crm.phonecall'].read_group([
                ('partner_id', '=', partner.id),
                ('asterisk_user_type', '=', 'technical')
            ], fields=['length', 'date'], groupby=['date'])

            partner.technical_minutes = sum(call['length'] for call in technical_calls)/60
            partner.technical_minutes_cur_month = sum(call['length'] for call in technical_calls if call['date'] == cur_date)/60