# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp

class ResPartner(models.Model):
    _inherit = "res.partner"

    average_sale_margin = fields.Monetary(compute='_compute_average_sale_margin', string="Average margin",
                                   digits=dp.get_precision('Product Price'))

    @api.multi
    def _compute_average_sale_margin(self):
        partner_id = 'partner_id'
        domain = [(partner_id, 'child_of', self.ids)]
        res = dict((item[partner_id][0], item['margin'] / item['partner_id_count']) for item in
             self.env['sale.order'].read_group(domain, [partner_id, 'margin'], [partner_id], orderby='id'))
        for partner in self:
            partner.average_sale_margin = res[partner.id]
