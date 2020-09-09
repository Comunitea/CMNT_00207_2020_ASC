# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class ResPartner(models.Model):
    _inherit = "res.partner"

    average_sale_margin = fields.Float(
        compute="_compute_average_sale_margin",
        string="Average margin (%)",
        digits=dp.get_precision("Product Price"),
    )
    total_sale_margin = fields.Monetary(
        compute="_compute_average_sale_margin", string="Average margin (€)"
    )

    @api.multi
    def _compute_average_sale_margin(self):
        for partner in self:
            domain = [("partner_id", "child_of", partner.ids), ("state", "in", ("done", "sale"))]
            sales = self.env['sale.order'].search(domain)
            margins = []
            totals = []
            for sale in sales:
                totals.append(sale.margin)
                margins.append((sale.margin / sale.amount_untaxed) * 100)
            
            partner.total_sale_margin = sum(totals)/float(len(totals))
            partner.average_sale_margin = sum(margins)/float(len(margins))
