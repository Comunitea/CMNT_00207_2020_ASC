# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    @api.multi
    def write(self, vals):
        state = vals.get('state', False)
        if state:
            if state in ('done', 'cancel'):
                vals['date'] = fields.Datetime.today()
        return super().write(vals)

