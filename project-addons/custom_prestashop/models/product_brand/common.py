# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields
from odoo.addons.component.core import Component


class ProductBrand(models.Model):
    _inherit = 'product.brand'

    prestashop_bind_ids = fields.One2many(
        comodel_name='prestashop.product.brand',
        inverse_name='odoo_id',
        string='PrestaShop Bindings',
    )


class PrestashopProductBrand(models.Model):
    _name = 'prestashop.product.brand'
    _inherit = 'prestashop.binding.odoo'
    _inherits = {'product.brand': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='product.brand',
        required=True,
        ondelete='cascade',
        string='Sale Order State',
        oldname='openerp_id',
    )


class ProductBrandAdapter(Component):
    _name = 'prestashop.product.brand.adapter'
    _inherit = 'prestashop.adapter'
    _apply_on = 'prestashop.product.brand'
    _prestashop_model = 'manufacturers'
