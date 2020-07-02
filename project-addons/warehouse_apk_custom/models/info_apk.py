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

    @api.model
    def get_wh_code_filter(self):
        wh_code_ids = ['']
        for obj in self.search([]):
            wh_code_ids += [obj.wh_code]
        print ('\n.....................\nCanlculando filteros: {}'.format(wh_code_ids))
        return wh_code_ids


class CrmTeam(models.Model):
    _name = 'crm.team'
    _inherit = ['info.apk', 'crm.team']

    wh_code = fields.Char('Wh code')

    def m2o_dict(self, field):
        if field:
            return {'id': field.id, 'name': field.name, 'wh_code': field.wh_code or field.name[:1]}
        else:
            return {'id': False}



class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherit = ['info.apk', 'delivery.carrier']

    wh_code = fields.Char('Wh code')

    def m2o_dict(self, field):
        if field:
            return {'id': field.id, 'name': field.name, 'wh_code': field.wh_code or field.code[:1]}
        else:
            return {'id': False}