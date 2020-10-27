##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2019 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
#    Vicente Ángel Gutiérrez <vicente@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wh_code = fields.Char(string="Unique WH Code")

    @api.multi
    @api.depends("default_code", "barcode")
    def _compute_wh_code(self):
        for product in self:
            if product.barcode:
                product.wh_code = product.barcode
            elif product.default_code:
                product.wh_code = product.default_code
            else:
                bind_id = product.prestashop_bind_ids and product.prestashop_bind_ids[0]
                if bind_id:
                    product.wh_code = ".%06d." % bind_id.prestashop_id
                else:
                    product.wh_code = ".9%05d." % product.id


class ProductProduct(models.Model):
    _inherit = "product.product"

    code_ignored = fields.Char(string="Codes to ignore as Serial")

    @api.multi
    def check_unreserve_more_qty(self):
        ##
        domain = [('move_id.product_id', 'in', self.ids),
                  ('location_id', 'child_of', 13),
                  ('move_id.product_id.tracking', '=', 'serial'),
                  ('qty_done', '=', 0),
                  ('state', '=', 'assigned')]

        sml_ids = self.env['stock.move.line'].search(domain)
        sm_ids = sml_ids.mapped('move_id')
        if sm_ids:
            sql = "delete from stock_move_line where id in %s"
            params = [tuple(sml_ids.ids)]
            self._cr.execute(sql, params)
            sql = "update stock_move set state = 'partially_available' where id in %s"
            params = [tuple(sm_ids.ids)]
            self._cr.execute(sql, params)
            self._cr.commit()
            self.check_reserved_quantity()
            sm_ids._action_assign()

    @api.multi
    def check_reserved_quantity(self):
        ##
        for product_id in self:
            quant_domain = [('location_id', 'child_of', 13),
                            ('product_id', '=', product_id.id),
                            ('reserved_quantity', '!=', 0),
                            ('lot_id', '!=', False)]
            sq_ids = self.env['stock.quant'].search(quant_domain)
            lot_ids = sq_ids.mapped('lot_id')
            quants_to_update = self.env['stock.quant']
            _logger.info ('Se han encontrado %d lotes para el producto %s reservados'%(len(lot_ids), product_id.display_name))
            for sq_id in sq_ids:
                move_domain = [('location_id', '=', sq_id.location_id.id),
                               ('state', '=', 'assigned'),
                               ('product_uom_qty', '=', 1),
                               ('lot_id', '=', sq_id.lot_id.id)]
                sml_ids = self.env['stock.move.line'].search(move_domain)
                if not sml_ids:
                    _logger.info ('El lote %s no tiene ningún ningún movimiento pero tiene una reserva en el quant'% sq_id.lot_id.name)
                    quants_to_update |= sq_id
                elif len(sml_ids) > 1:
                    _logger.info("Error de movimientos. Mas de un movimiento para el lote (%d) %s"%(sq_id.lot_id.id, sq_id.lot_id.name))
                    for sml_id in sml_ids:
                        _logger.info('>>> El lote %s en el albaran %s (movimiento %s)'%(sml_id.lot_id.name, sml_id.picking_id.name, sml_id.move_id.id))
                else:
                    _logger.info("Quant correcto: Lote %s en albarán %s, movimiento %s" %(sq_id.lot_id.name, sml_ids.picking_id.name, sml_ids.move_id.id))

        if quants_to_update:
            _logger.info('Se corrige y se pone a cero las reservas en los lotes %s' %quants_to_update.mapped('lot_id.name'))
            quants_to_update.sudo().write({'reserved_quantity':0})




    def return_fields(self, mode="tree"):
        return [
            "id",
            "display_name",
            "default_code",
            "list_price",
            "qty_available",
            "virtual_available",
            "tracking",
            "wh_code",
        ]

    def m2o_dict(self, field):
        if field:
            return {
                "id": field.id,
                "name": field.apk_name,
                "default_code": field.default_code,
                "barcode": field.barcode,
                "wh_code": field.wh_code,
            }
        else:
            return {"id": False}
