# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    invoice_on_company = fields.Many2one("res.company")
