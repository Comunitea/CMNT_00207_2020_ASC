# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models



class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self):
        res = super()._action_done()
        for move in self.filtered(lambda r: r.rma_line_id):
            move.rma_line_id.rma_id.write({'reception_date': fields.Date.today()})
        return res
