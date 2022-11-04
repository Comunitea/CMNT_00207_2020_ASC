# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    volume_factor = fields.Float("% Boxed Volumen", default=100, help="% of increment volume to compute ")
    volume_packed_factor = fields.Float("% Paked Volumen", default=100, help="% of increment volume when packed to compute ")
    volume = fields.Float(default=0.0005, digits=(16,5))


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends('product_variant_ids', 'product_variant_ids.volume_packed_factor')
    def _compute_volume_packed_factor(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.volume_packed_factor = template.product_variant_ids.volume_packed_factor
            
        for template in (self - unique_variants):
            template.volume_packed_factor = 0.0

    @api.one
    def _set_volume_packed_factor(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.volume_packed_factor = self.volume_packed_factor

    @api.depends('product_variant_ids', 'product_variant_ids.volume_factor')
    def _compute_volume_factor(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.volume_factor = template.product_variant_ids.volume_factor
        for template in (self - unique_variants):
            template.volume_factor = 0.0

    @api.one
    def _set_volume_factor(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.volume_factor = self.volume_factor

    volume_factor = fields.Float(
        '% Boxed Volumen', compute='_compute_volume_factor', inverse='_set_volume_factor',
        help="The volume in m3.  increment volume when packed to customer", store=True)
    volume_packed_factor = fields.Float(
        '% Boxed Packed Volumen', compute='_compute_volume_packed_factor', inverse='_set_volume_packed_factor',
        help="The volume in m3.", store=True)
