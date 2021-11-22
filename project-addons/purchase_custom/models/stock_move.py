# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import logging


_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'
 
    
    def reassing_split_from_picking(self):
        
        res = super().reassing_split_from_picking()
        if res:
            res |= self.mapped('picking_id')
            for pick in res:
                pick.write_advise_affected_picks()
        return res