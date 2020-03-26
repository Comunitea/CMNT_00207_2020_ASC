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
        partner_id = "partner_id"
        domain = [
            (partner_id, "child_of", self.ids),
            ("state", "in", ("done", "sale")),
        ]
        vals = self.env["sale.order"].read_group(
            domain,
            [partner_id, "margin", "amount_untaxed"],
            [partner_id],
            orderby="id",
        )
        res = dict(
            (
                item[partner_id][0],
                {
                    "count": item["partner_id_count"],
                    "margin": item["margin"],
                    "amount": item["amount_untaxed"],
                },
            )
            for item in vals
        )
        for partner in self:
            rp = res.get(partner.id)
            if rp:
                partner.total_sale_margin = rp["margin"] / rp["count"]
                partner.average_sale_margin = rp["margin"] / rp["amount"] * 100
