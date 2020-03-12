# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.addons.crm.models import crm_stage


class CrmLead(models.Model):

    _inherit = 'crm.lead'

    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES)
