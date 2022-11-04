# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class StockMove(models.Model):
    _inherit = "stock.move"
    

    serial_inventory_id = fields.Many2one("stock.serial.inventory")


    def filter_affected_moves(self):
        return super().filter_affected_moves().filtered(lambda x: not x.serial_inventory_id)
        