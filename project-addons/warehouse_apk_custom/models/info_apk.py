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


class CrmTeam(models.Model):
    _name = 'crm.team'
    _inherit = ['info.apk', 'crm.team']

    wh_code = fields.Char('Wh code')

    def m2o_dict(self, field):
        if field:
            return {'id': field.id, 'name': field.wh_code}
        else:
            return {'id': False}

class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherit = ['info.apk', 'delivery.carrier']

    wh_code = fields.Char('Wh code')

    def m2o_dict(self, field):
        if field:
            return {'id': field.id, 'name': field.wh_code}
        else:
            return {'id': False}