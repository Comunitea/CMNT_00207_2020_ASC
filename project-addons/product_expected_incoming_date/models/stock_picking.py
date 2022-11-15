# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.one
    def _set_scheduled_date(self):
        vals = {'date_expected': self.scheduled_date}
        if self.state != 'done':
            vals.update(date = self.scheduled_date)
        self.move_lines.write(vals)
