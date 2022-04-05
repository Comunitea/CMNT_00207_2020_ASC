# © 2022 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CrmTeam(models.Model):

    _inherit = 'crm.team'

    automatic_leads = fields.Boolean()
