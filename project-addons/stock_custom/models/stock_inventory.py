# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockInventory(models.Model):
    _inherit = "stock.inventory"


    def action_validate(self):
        ## Compruebo que no haya ningún movimiento pendiente para este ajuste
        for inventory_id in self:
            product_ids = inventory_id.line_ids.mapped('product_id')
            domain = [('qty_done', '!=', 0), ('product_id', 'in', product_ids.ids), ('state', '!=', 'done')]
            sml_ids = self.env['stock.move.line'].search(domain)
            if sml_ids:
                msg = ''
                for sml_id in sml_ids:
                    msg='{}\n{} -> {}'.format(msg, sml_id.move_id.picking_id.name, sml_id.product_id.display_name, sml_id.product_uom_qty)

                raise ValidationError('Los siguientes albaranes y artículos están pendientes de realizarse. Pon las cantidades hechas a 0 antes de realizar el ajuste de inventario:\n{}'.format(msg))
        return super().action_validate()



