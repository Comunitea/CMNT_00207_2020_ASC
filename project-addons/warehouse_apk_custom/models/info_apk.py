from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class InfoApk(models.AbstractModel):
    _inherit = 'info.apk'

    def get_apk_product(self, code):
        product_domain = [('wh_code', '=', code)]
        product_id = self.env['product.product'].search(product_domain).filtered(lambda x: x.default_on)
        if len(product_id)>1:
            raise ValueError ('Se han encontrado varios productos para este código {}'.format(code))
        return product_id

    @api.model
    def get_wh_code_filter(self, values):
        field = values.get('field', False)
        if not field:
            return
        res = []
        if self.fields_get()[field]['type'] == 'selection':
            res = self.get_selection_dict_values(field)
        if self.fields_get()[field]['type'] == 'many2one':
            res = self.get_many2one_dict_values(field)
        print("GET_WH_CODE_FILTER para {} con values: {}: Devuelvo {}".format(self._name, values, res))
        return res


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
            return {'id': field.id, 'name': field.name, 'wh_code': field.wh_code or field.code and field.code[:1]}
        else:
            return {'id': False}