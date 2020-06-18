from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class InfoApk(models.AbstractModel):
    _inherit = 'info.apk'

    def get_apk_product(self, code):
        product_domain = [('wh_code', '=', code)]
        product_id = self.env['product.product'].search(product_domain).filtered(lambda x: not x._is_phantom_bom())
        if len(product_id)>1:
            raise ValueError ('Se han encontrado varios productos para este código {}'.format(code))
        return product_id


