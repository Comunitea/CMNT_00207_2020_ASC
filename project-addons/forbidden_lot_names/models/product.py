# © 2016 Comunitea - Javier Colmenero <javier@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class NotLotName(models.Model):
    _name="not.lot.name"

    name = fields.Char('Nombre no válido')
    product_id = fields.Many2one('product.product', string='Artículo')

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.product_variant_ids.act_not_lot_names()
        return res


class ProductProduct(models.Model):

    _inherit = "product.product"

    not_lot_name_ids = fields.One2many('not.lot.name', 'product_id', string='Lotes no válidos')

    def get_fields_to_find_names(self):
        return ['default_code', 'barcode']
    
    @api.multi
    def write(self, vals):
        res = super().write(vals)
        for field in self.get_fields_to_find_names():
            if field in vals:
                self.act_not_lot_names()
                break
        return res
    
    @api.model
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        res.act_not_lot_names()
        return res
    
    @api.multi
    def act_not_lot_names(self):
        SLN = self.env['not.lot.name']
        fields = self.get_fields_to_find_names()
        for product_id in self.filtered(lambda x: x.tracking != 'none'):
            not_names = product_id.not_lot_name_ids.mapped('name')
            for field in fields:
                if product_id[field] and product_id[field] not in not_names:
                    values = {'name': product_id[field], 'product_id': product_id.id}
                    SLN.create(values)
        