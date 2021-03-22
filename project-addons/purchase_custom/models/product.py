# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from datetime import datetime, timedelta

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        pt_id = vals.get('product_tmpl_id', False)
        if pt_id:
            template_id = self.env['product.template'].browse(pt_id)
            tracking = template_id.tracking
            msg = '<ul>'
            for val in vals.keys():
                msg += "<li> %s : %s </li> "% (val, vals[val])
            msg += '</ul>'
            template_id.message_post("Se ha creado una nueva variante para %s %s. Seguimiento: %s"%(template_id.display_name, msg, tracking))

        new_id = super().create(vals)
        if new_id.tracking != tracking:
            template_id.message_post("<strong>Se ha cambiado el tracking del artículo</strong>")
        return new_id
