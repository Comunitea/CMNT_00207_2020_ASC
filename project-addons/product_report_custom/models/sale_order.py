# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta

class SaleOrder(models.Model):

    _inherit = "sale.order"

    @api.multi
    def write(self, vals):
        res = super().write(vals=vals)
        if 'state' in vals:
            self.mapped('order_lines').mapped('product_id').compute_product_sale_alarm()




