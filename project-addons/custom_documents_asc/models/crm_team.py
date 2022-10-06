# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CrmTeam(models.Model):

    _inherit = "crm.team"

    team_tag_line = fields.Char()
    team_name = fields.Char(string="Company Name")
    team_logo = fields.Binary(rstring="Company Logo")
    team_email = fields.Char(string="Email")
    team_phone = fields.Char(string="Phone")
    team_website = fields.Char(string="Web")
    css_class = fields.Many2one("crm.class")
    team_accounts = fields.Text(string="Accounts")
    neutral_document = fields.Boolean()
    overwrite_company_in_docs = fields.Boolean("Overwrite footer company", default=False)