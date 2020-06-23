#######################################################################

from odoo import api, models, fields

class StockLocation(models.Model):
    _inherit = 'stock.location'

    def m2o_dict(self, field):
        if field:
            return {'id': field.id, 'name': field.apk_name, 'oldname': field.oldname}
        else:
            return {'id': False}