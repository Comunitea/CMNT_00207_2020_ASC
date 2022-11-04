from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["apk.model", "product.product"]

    wh_code = fields.Char(string="Unique WH Code")

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            product_ids = []
            if operator in positive_operators:
                product_ids = self._search([('wh_code', '=', name)] + args, limit=limit,
                                           access_rights_uid=name_get_uid)
            if product_ids:
                return self.browse(product_ids).name_get()
        return super()._name_search(name=name, args=args, operator=operator, limit=100, name_get_uid=name_get_uid)

    @api.multi
    def get_apk_values(self, values={}):
        res = []
        vals = {}
        mode = values.get('mode', False)
        error = ''
        for product_id in self:
            display_name = "{}".format(product_id.display_name)
            if mode == 'test':
                vals = {'id': product_id.id}
            else:
                vals = {
                    'id': product_id.id,
                    'name': display_name,
                    'barcode': product_id.barcode,
                    'default_code': product_id.default_code or '',
                    'tracking': product_id.tracking,
                    'template_tracking': product_id.virtual_tracking}
            # _logger.info("%s"%display_name)       
            # _logger.info("%s"%vals)       
            res += [vals]
        # _logger.info("%s"%error)       
        return res

    @api.model
    def ProductData(self, values):
        domain = values.get('domain', [('product_tmpl_id.name', '!=', False), ('default_code', '!=', False), ('type', '!=', 'service')])
        _logger.info("RECUPERANDO ARTICULOS con:%s"%domain)
        limit = values.get('limit', 10)
        offset = values.get('offset', 0)
        product_ids = self.search(domain, offset= offset, limit=limit)
        _logger.info(">>> %d artículos" %len(product_ids))
        return product_ids.get_apk_values(values)

