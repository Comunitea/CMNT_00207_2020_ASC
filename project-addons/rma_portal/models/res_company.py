# © 2022 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompany(models.Model):

    _inherit = 'res.company'

    return_default_operation_id = fields.Many2one('rma.operation')
    rma_default_operation_id = fields.Many2one('rma.operation')

    def get_rma_operation_type(self, operation_type):
        if operation_type == 'return':
            return self.return_default_operation_id.id
        else:
            return self.rma_default_operation_id.id
