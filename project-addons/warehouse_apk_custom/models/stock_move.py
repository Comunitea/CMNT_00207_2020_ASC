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

    @api.model
    def create_move_lots(self, vals):

        move_id = vals.get('id', False)
        lot_names = vals.get('lot_names', False)
        move = self.browse(move_id)
        active_location_id = vals.get('active_location', False)
        if not move_id or not lot_names:
            return False
        ##Voy a hacer un write al final de la cantidad y el estado
        sml_ids_to_update = []

        ## Los moviemintos que no tengan lotes, le añado los que tengo, si no llegan añado nuevo. No borro ningún movimiento.
        ## Podría utilizar el lot_name pero me parece más limpio así, se crean y se añaden a los stock_move_line pq sino tendríamos
        ## distinta lógica según el tipo de albarán
        new = False

        ## Actulizazo como hechos los movimientos que tengan lote en la lista y los quito para no crearlos
        if not active_location_id:
            active_location = move.active_location_id or move.move_line_location_id
            active_location_id = active_location.id
        sml_with_lot_ids = move.move_line_ids.filtered(lambda x: x.lot_id.name in lot_names)
        sml_ids_to_update += sml_with_lot_ids.ids
        lot_names -= sml_with_lot_ids.mapped('lot_id.name')
        if lot_names:
            lot_ids = self.env['stock.production.lot']
            for lot in lot_names:
                lot_id = lot_ids.find_or_create_lot(lot, move.product_id, not move.picking_type_id.use_existing_lots)
                if lot_id:
                    lot_ids |= lot_id


        if new:
            for sml_id in sml_with_lot_ids:
                sml_id.write_status('lot_id', 'done')
                #sml_id[move.default_location] = active_location_id
                if move.active_location_id:
                    sml_id.write_status(move.default_location, 'done')
                if move.tracking == 'serial':
                    sml_id.write_status('qty_done', 'done')
                    sml_id.write_status(move['default_location'], 'done')
                    sml_id.qty_done = 1
                lot_names.pop(lot_names.index(sml_id.lot_id.name))

        ##Si aún quedan lotes
        if lot_names:
            ## encuentro o creo los lotes que falten
            lot_ids = self.env['stock.production.lot']
            for lot in lot_names:
                lot_id = lot_ids.find_or_create_lot(lot, move.product_id, not move.picking_type_id.use_existing_lots)
                if lot_id:
                    lot_ids |= lot_id

            ##filtro todos los movimientos que no tengan lote y se lo añado
            sml_ids = move.move_line_ids.filtered(lambda x: not x.lot_id or not x.read_status('lot_id', 'done'))
            for sml in sml_ids:
                ## Por cada movimiento quito el primero, genero nueva reserva forzando el lote
                if not lot_ids:
                    break
                if move.location_id.should_bypass_reservation()\
                    or move.product_id.type == 'consu':
                    sml.lot_id = lot_ids[0]
                    lot_ids -= lot_ids[0]
                    new_move = sml
                else:
                    sml.unlink()
                    reserved = move._update_reserved_quantity(1, 1, move.location_id, lot_id=lot_ids[0], strict=False)

                    if not reserved:
                        ## buscon el move line con ese lote
                        ocup_dom = [('move_id.picking_type_id', '=', move.picking_type_id.id),
                                    ('product_id', '=', move.product_id.id),
                                    ('state', 'in', ('assigned', 'partially_available')),
                                    ('lot_id', '=', lot_ids[0].id)]
                        ocup_move_line = self.env['stock.move.line'].search(ocup_dom)
                        if ocup_move_line:
                            move_to_update = ocup_move_line.move_id
                            ocup_move_line.unlink()
                            reserved = move._update_reserved_quantity(1, 1, move.location_id, lot_id=lot_ids[0], strict=False)
                            if move_to_update._update_reserved_quantity(1, 1, move.location_id, strict=False) == 1:
                                move_to_update.write({'state': 'assigned'})
                    if not reserved:
                        raise ValidationError('No se ha podido reservar el lote {}'.format(lot_ids[0]))
                    move.write({'state': 'assigned'})
                    lot_ids -= lot_ids[0]
                    new_move = move.move_line_ids[-1]

                new_move.write_status('lot_id', 'done')
                new_move.qty_done = 1
                new_move.write_status('qty_done', 'done')
                #new_move[move.default_location] = active_location_id
                if move.active_location_id or active_location_id and move.tracking == 'serial':
                    new_move.write_status(move.default_location, 'done')
            ## Si quedan lotes, tengo que crear un movieminto por cada lote
            if lot_ids:
                for lot_id in lot_ids:
                    if move.quantity_done >= move.reserved_availability:
                        break
                    reserved = move._update_reserved_quantity(1, 1, move.location_id, lot_id=lot_id, strict=False)
                    if reserved:
                        new_move = move.move_line_ids[-1]
                        new_move.write_status('lot_id', 'done')
                        new_move.qty_done = 1
                        new_move.write_status('qty_done', 'done')
                        new_move[move.default_location] = active_location_id
                        if move.active_location_id:
                            new_move.write_status(move.default_location, 'done')
        move._recompute_state()
        ## Devuelvo la información del moviemitno para ahorrar una llamada desde la apk
        values = {'id': move.id, 'model': 'stock.move', 'view': 'form', 'filter_move_lines': vals.get('filter_move_lines', 'Todos')}
        if not move.picking_type_id.allow_overprocess and move.quantity_done > move.reserved_availability:
            raise ValidationError("No puedes procesar más cantidad de lo reservado para el movimiento")
        return self.env['info.apk'].get_apk_object(values)