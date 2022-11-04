# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    active = fields.Boolean("Active", default=True)

    @api.multi
    @api.constrains('product_id', 'name')
    def _check_name_validity(self):
        for lot in self:
            not_names = self.product_id.not_lot_name_ids.mapped('name')
            if lot.name in not_names:
                raise ValidationError ("El lot {} no es válido para el arículo {}".format(lot.name, lot.product_id.display_name))    
