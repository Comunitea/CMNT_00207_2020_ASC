# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProductProduct(models.Model):

    _inherit = 'product.product'
    pack_components = fields.Many2many('product.product', compute='_compute_pack_compoents')

    def _compute_pack_compoents(self):
        for product in self:
            pack_prods = self.env['product.product']
            bom = self.env["mrp.bom"]._bom_find(product=product)
            if bom and bom.type == "phantom":
                pack_prods = bom.mapped('bom_line_ids.product_id')
            product.pack_components = pack_prods
