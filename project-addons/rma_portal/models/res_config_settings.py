# © 2022 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    return_default_operation_id = fields.Many2one('rma.operation', related='company_id.return_default_operation_id', readonly=False)
    rma_default_operation_id = fields.Many2one('rma.operation', related='company_id.rma_default_operation_id', readonly=False)
