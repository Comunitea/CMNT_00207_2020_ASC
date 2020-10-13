# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class MrpBom(models.Model):

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.product_tmpl_id.product_variant_ids._compute_pack_product()
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get('product_tmpl_id'):
            self.mapped('product_tmpl_id.product_variant_ids')._compute_pack_product()
        return res
