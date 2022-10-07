# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    ic_journal_id = fields.Many2one('account.journal', string="Intercompany Journal")
    purchase_ic_journal_id = fields.Many2one('account.journal', string="Intercompany Purchase Journal")

