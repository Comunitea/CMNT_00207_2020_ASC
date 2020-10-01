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
            if sales:
                for sale in sales:
                    totals.append(sale.margin)
                    if sale.amount_untaxed > 0:
                        margins.append((sale.margin / sale.amount_untaxed or 1) * 100)
                    else:
                        margins.append(0)
                
                partner.total_sale_margin = sum(totals)/float(len(totals))
                partner.average_sale_margin = sum(margins)/float(len(margins))
            else:
                partner.total_sale_margin = 0.0
                partner.average_sale_margin = 0.0