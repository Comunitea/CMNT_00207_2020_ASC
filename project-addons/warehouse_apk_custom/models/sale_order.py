# -*- coding: utf-8 -*-

from odoo import api, models, fields

class SaleOrder(models.Model):

    _inherit = 'sale.order'

    @api.model
    def get_modal_info(self, values):
        res = super().get_modal_info(values=values)
        id = int(values.get('id'))
        sale_id = self.browse(id)
        res['team_id'] = {'id': sale_id.team_id.id, 'name': sale_id.team_id.name},
        return res