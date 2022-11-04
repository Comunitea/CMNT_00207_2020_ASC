# Copyright (C) 2011 Julius Network Solutions SARL <contact@julius.fr>
# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class StockMoveLocationWizardLine(models.TransientModel):
    _inherit = "wiz.stock.move.location.line"
    
    @api.multi
    def _get_move_line_values(self, picking, move):
        res = super()._get_move_line_values(picking=picking, move=move)
        if self.product_id.virtual_tracking:
            domain = [('product_id', '=', self.product_id.id), ('real_location_id', '=', self.origin_location_id.id)]
            lot_ids = self.env['stock.production.lot'].search(domain)
            if lot_ids:
                res['lot_ids'] = [(6,0, lot_ids.ids)]
        return res