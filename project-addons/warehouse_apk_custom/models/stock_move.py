# -*- coding: utf-8 -*-
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
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

BINARYPOSITION = {'product_id': 0, 'location_id': 1, 'lot_id': 2, 'package_id': 3, 'location_dest_id': 4, 'result_package_id': 5, 'qty_done': 6}
FLAG_PROP = {'view': 1, 'req': 2, 'done': 4};

class StockMove(models.Model):
    _inherit = 'stock.move'

    def update_move_lot_apk(self, move, lot_ids, active_location=False):

        if move.product_id.tracking != 'serial':
            raise ValidationError('El producto %s no tiene tracking por número de serie'% move.product_id.display_name)
        print ('Actualizo el movimiento %d con lote (s) %s' % (move.id, lot_ids.mapped('name')))
        if not active_location:
            active_location = move.active_location_id or move.move_line_location_id
        sml_ids_to_update = self.env['stock.move.line']
        sml_with_lot_ids = move.move_line_ids.filtered(lambda x: x.lot_id in lot_ids)
        sml_no_lot_ids = move.move_line_ids - sml_with_lot_ids - move.move_line_ids.filtered(lambda x: x.qty_done == 1)
        lot_ids -= sml_with_lot_ids.mapped('lot_id')
        sml_ids_to_update += sml_with_lot_ids
        move_to_rereserve = self.env['stock.move']
        for sml_id in sml_no_lot_ids:

            if not lot_ids:
                continue
            lot = lot_ids[0]
            # Busco un movimiento que tenga esa reserva
            if True:
                domain = [('state', '=', 'assigned'),
                          ('move_id', '!=', move.id),
                          ('move_id.location_id', '=', move.location_id.id),
                          ('qty_done', '=', 0),
                          ('lot_id', '=', lot.id),
                          ]
                to_unreserve = self.env['stock.move.line'].search(domain)
                if len(to_unreserve)>1:
                    raise ValidationError('Tienes 2 movimientos asignados con el mismo numero de serie o no hay disponibilidad para el lote %s'%lot.name)
                if to_unreserve:
                    print ('-->> Desreservamos el movimiento %d con lote %s'%(to_unreserve.id, lot_ids.mapped('name')))
                    sql=1
                    if sql:
                        #Intercambio solo el lote id y las ubicaciones en los move_line_ids
                        sql = "update stock_move_line set location_id = %d,location_dest_id = %d,lot_id = %d where id = %d; " \
                              "update stock_move_line set location_id = %d,location_dest_id = %d,lot_id = %d where id = %d; "\
                              %(sml_id.location_id.id,
                                sml_id.location_dest_id.id,
                                sml_id.lot_id.id,
                                to_unreserve.id,
                                to_unreserve.location_id.id,
                                to_unreserve.location_dest_id.id,
                                to_unreserve.lot_id.id,
                                sml_id.id,
                                )
                        self._cr.execute(sql)
                        sml_ids_to_update += sml_id
                        lot_ids -= lot
                        continue
                    else:
                        move_to_rereserve += to_unreserve.mapped('move_id')
                        to_unreserve.unlink()

            #Si es una entrada o similar .....
            if move.location_id.should_bypass_reservation() \
                    or move.product_id.type == 'consu':
                sml_id.lot_id = lot
                lot_ids -= lot
                sml_ids_to_update += sml_id
                continue
            sml_id.unlink()
            reserved = move._update_reserved_quantity(1, 1, move.location_id, lot_id=lot, strict=False)
            print('-->> Reservamos el movimiento %d con lote %s' % (move.id, lot.name))
            if not reserved:
                raise ValidationError('No se ha podido reservar el lote {}'.format(lot.name))
            # Añado el move line a la lista de movimientos para actualizar
            sml_ids_to_update += move.move_line_ids.filtered(lambda x: x.lot_id == lot)
            #move.move_line_ids[-1][move.default_location] = active_location.id
            lot_ids -= lot


        if lot_ids and move.picking_type_id.allow_overprocess:
            print('-->> Creamos nuevos movimientos para los lotes%s' % lot_ids.mapped('name'))
            for lot_id in lot_ids:
                if move.quantity_done >= move.reserved_availability:
                    break
                reserved = move._update_reserved_quantity(1, 1, move.location_id, lot_id=lot_id, strict=False)
                if reserved:
                    sml_with_lot_ids += move.move_line_ids[-1]

        if sml_ids_to_update:
            print('-->> Actualizo los movimientos con lotes: %s' % sml_ids_to_update.mapped('lot_id.name'))
            vals = {}
            ##para no llamar a write_status para todos llamo a uno y escribo al resto
            sml_id = sml_ids_to_update[0]
            sml_id.write_status('lot_id', 'done')
            if move.active_location_id:
                sml_id.write_status(move.default_location, 'done')
            if move.tracking == 'serial':
                sml_id.write_status('qty_done', 'done')
                sml_id.write_status(move['default_location'], 'done')
                sml_id.qty_done = 1
                vals['qty_done'] = 1

            if len(sml_ids_to_update)>1:
                vals['field_status_apk'] = sml_id.field_status_apk
                sml_ids_to_update[1:].write(vals)

        if move_to_rereserve:
            print('-->> Reservamos de nuevo los movimientos (stock move) para los lotes %s' % move_to_rereserve.mapped('name'))
            move_to_rereserve._action_assign()
        return move

    @api.model
    def create_move_lots(self, vals):

        move_id = vals.get('id', False)
        lot_names = vals.get('lot_names', False)
        if not lot_names:
            raise ValidationError("No has enviado ningún lote valido")
        move = self.browse(move_id)
        if not move:
            raise ValidationError("No has enviado ningún movimiento válido")

        #Recupero la ubicación activa o la establezco por defecto
        active_location_id = vals.get('active_location', False)
        if lot_names:
            lot_ids = self.env['stock.production.lot']
            for lot in lot_names:
                lot_id = lot_ids.find_or_create_lot(lot, move.product_id, not move.picking_type_id.use_existing_lots)
                if lot_id:
                    lot_ids |= lot_id

        move.update_move_lot_apk(move, lot_ids, active_location=False)
        move._recompute_state()
        ## Devuelvo la información del moviemitno para ahorrar una llamada desde la apk
        values = {'id': move.id, 'model': 'stock.move', 'view': 'form', 'filter_move_lines': vals.get('filter_move_lines', 'Todos')}
        if not move.picking_type_id.allow_overprocess and move.quantity_done > move.reserved_availability:
            raise ValidationError("No puedes procesar más cantidad de lo reservado para el movimiento")
        return self.env['info.apk'].get_apk_object(values)
