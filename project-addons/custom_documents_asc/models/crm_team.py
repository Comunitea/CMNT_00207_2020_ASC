# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.addons.crm.models import crm_stage


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    team_tag_line = fields.Char()
    team_name = fields.Char(string='Company Name')
    team_logo = fields.Binary(string="Company Logo")
    css_class = fields.Selection([('Asec', 'A-Sec'),('Outlet', 'Outlet')], "Tipo de CSS")