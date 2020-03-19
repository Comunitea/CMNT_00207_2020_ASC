# -*- coding: utf-8 -*-
# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

class NewSPLotLineWzd(models.TransientModel):
    _name = 'new.splot.line.wzd'

    wzd_id = fields.Many2many('new.splot.wzd')
    name = fields.Char('Lot')



class NewSPLotWzd(models.TransientModel):
    """Wzd to select pack for pack move
    """

    _name = 'new.splot.wzd'
    _description = 'Asistente para empaquetar'

    move_id = fields.Many2one('stock.move', 'Move')
    product_id = fields.Many2one('product.product', 'Product')
    line_ids = fields.One2many('new.splot.line.wzd', 'wzd_id', 'Lines')

    @api.multi
    def action_create_new_lots(self):
        return