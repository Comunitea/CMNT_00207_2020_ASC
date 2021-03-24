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

    def reserve_not_free_lots(self, move, move_ids, lot_ids):
        ### BUSCO DE LOS LOTES QUE QUEDAN, LOS QUE NO ESTÁN RESERVADOS
        _logger.info(u"Busco en otros movimeintos que ya estén resevados para intercambiarlos")

        sml_ids_to_update = self.env['stock.move.line']
        sml_no_lot_ids = move_ids.filtered(lambda x: x.qty_done == 0 and x.lot_id not in lot_ids)
        domain = [('state', '=', ['partially_available', 'assigned']),
                  ('move_id', '!=', move.id),
                  ('move_id.product_id', '=', move.product_id.id),
                  ('location_id', 'child_of', move.location_id.id),  # No tienen porque estar en la misma estanteria
                  ('lot_id', 'in', lot_ids.ids)]
        sml_ids =  self.env['stock.move.line'].search(domain)
        ## Si hay alguno ya hecho, entonces error
        done_sml_ids = sml_ids.filtered(lambda x: x.qty_done)
        if done_sml_ids:
            msg = u'Estos lotes están hechos: '
            for done_sml_id in done_sml_ids:
                msg = u'{} {} en {}, '.format(msg, done_sml_id.lot_id.name, done_sml_id.picking_id.name)
            _logger.info(u"No hay lotes ocupados")
            raise ValidationError(msg)
        ## Están todos con qty_done a 0
        sml_ids_to_unreserve = sml_ids
        if not  sml_ids_to_unreserve:
            _logger.info(u"No hay lotes ocupados")
            return sml_ids_to_update, lot_ids

        if sml_ids_to_unreserve:
            msg = "Los lotes {} están en otros movimientos y se intercambiarán".format(sml_ids_to_unreserve.mapped('lot_id.name'))
        else:
            msg = "No se ha encontrado nngún lote asignado fuera de este movimiento"
        _logger.info(msg)
        execute_sql = False
        for to_unreserve in sml_ids_to_unreserve:
            sml_id = sml_no_lot_ids[0]
            lot_id = to_unreserve.lot_id
            ##Intercambio los lotes de 2 movimientos
            sql = "update stock_move_line set location_id = %d,location_dest_id = %d,lot_id = %d where id = %d; " \
                  "update stock_move_line set location_id = %d,location_dest_id = %d,lot_id = %d where id = %d; " \
                  % (sml_id.location_id.id,
                     sml_id.location_dest_id.id,
                     sml_id.lot_id.id,
                     to_unreserve.id,
                     to_unreserve.location_id.id,
                     to_unreserve.location_dest_id.id,
                     to_unreserve.lot_id.id,
                     sml_id.id,
                     )
            msg = "Libero el lote {} en el movimiento, y lo traigo al movimiento {} con lote {}".format(lot_id.name, to_unreserve.id, sml_id.id, sml_id.lot_id.name)
            _logger.info(msg)
            self._cr.execute(sql)
            execute_sql = True
            sml_ids_to_update += sml_id
            sml_no_lot_ids -= sml_id
            lot_ids -= lot_id
        if execute_sql:
            self._cr.commit()
        return sml_ids_to_update, lot_ids

    def reserve_free_lots(self, move, move_ids, lot_ids):
        _logger.info(u"Busco en otros movimeintos que no estén resevados")
        sml_ids_to_update = self.env['stock.move.line']
        ### BUSCO DE LOS LOTES QUE QUEDAN, LOS QUE NO ESTÁN RESERVADOS
        while move_ids and lot_ids:
            move_id = move_ids[0]
            move_ids -= move_id
            lot_id = lot_ids[0]
            msg = "Libero el lote {} en el movimiento {}, y le asigno el  lote {}".format(move_id.lot_id.name, move_id.id, lot_id.name)
            _logger.info(msg)
            move_id.unlink()
            reserved = move._update_reserved_quantity(1, 1, move.location_id, lot_id=lot_id, strict=False)
            if not reserved:
                ## Esto a continuación es solo para ayudar a identificar el problema
                _logger.info ('No se ha podido reservar el lote {} poara el movimiento {}'.format(lot_id.name, move.display_name))
                domain = [('location_id', 'child_of', move.location_id.id),
                          ('product_id', '=', move.product_id.id),
                          ('lot_id', '=', lot_id.id)]
                quant = self.env['stock.quant'].search(domain)
                if not quant:
                    msg = '>>> No hay stock en {} para {} con serie {}'.format(
                        move.location_id.name, move.product_id.default_code, lot_id.name)
                    _logger.info(msg)
                    raise ValidationError(msg)

                elif quant.reserved_quantity != 0:
                    ## Busco el movimiento que lo está reservando
                    domain = [('location_id', 'child_of', move.location_id.id),
                              ('lot_id', '=', lot_id.id),
                              ('move_id.product_id', '=', move.product_id.id),
                              ('state', '=', 'assigned')]
                    moves = self.env['stock.move.line'].search(domain).mapped('move_id.display_name')
                    if not moves:
                        msg = '>>>No hay movimeito con origen {} para {} con serie {}'.format(move.location_id.name,
                                                                               move.product_id.default_code,
                                                                               lot_id.name)
                        _logger.info(msg)
                        raise ValidationError(msg)
                    msg = 'El stock en {} para {} con serie {} ya esta reservado y hecho para otro movimiento {}'.format(
                            move.location_id.name, move.product_id.default_code, lot_id.name, moves)
                    _logger.info(msg)
                    raise ValidationError(msg)
                else:
                    raise ValidationError('No se ha podido reservar. Causa desconocida')

            sml_ids_to_update += move.move_line_ids.filtered(lambda x: x.lot_id == lot_id)
            lot_ids -= lot_id
        return sml_ids_to_update, lot_ids

    def update_move_lot_apk(self, move, lot_ids, active_location=False, sql=True):
        if move.product_id.tracking != 'serial':
            raise ValidationError('El producto %s no tiene tracking por número de serie'% move.product_id.display_name)
        if not active_location:
            active_location = move.active_location_id or move.move_line_location_id

        sml_ids_to_update = self.env['stock.move.line']

        ## Quito los lotes que ya han sido leidos
        confirmed_lots = move.move_line_ids.filtered(lambda x: x.qty_done and x.lot_id in lot_ids)
        lot_ids -= confirmed_lots.mapped('lot_id')

        move_ids = move.move_line_ids.filtered(lambda x: not x.qty_done) - confirmed_lots

        ## Filtro los moviminetos que tienen lotes que el isuairo introduce. Si qty_done = 0 , los actualizo, si no los ignoro
        sml_with_lot_ids = move_ids.filtered(lambda x: x.lot_id in lot_ids)

        ## Los lotes que están en los movimeintos los saco del conjunto
        lot_ids -= sml_with_lot_ids.mapped('lot_id')

        # Los que no tienen qty_done, los meto to update
        sml_ids_to_update += sml_with_lot_ids.filtered(lambda x: x.qty_done == 0)

        # Me quedan los siguientes movimientos "libres" por estudiar
        move_ids = move_ids - sml_with_lot_ids
        if not lot_ids:
            if sml_ids_to_update:
                self.update_sml_ids(move, sml_ids_to_update)
            return move
        ## Es una entrada  ono requiere reservas
        if move.location_id.should_bypass_reservation() \
                or move.product_id.type == 'consu':
            while move_ids and lot_ids:
                move_id = move_ids[0]
                lot_id = lot_ids[0]
                move_id.lot_id = lot_id
                lot_ids -= lot_id
                move_ids -= move_id
                sml_ids_to_update += move_id

        else:
            ## Intercambio los lotes en los movimientos
            update_sml_ids, lot_ids = self.reserve_not_free_lots(move, move_ids, lot_ids)
            #Devuelve un listado de moviemitnos y lotes que tendo que actualizar y o no tocar mas, ademas, lot_ids le ha quitado unidades
            sml_ids_to_update += update_sml_ids
            move_ids -= update_sml_ids

            ## Pongo los lotes libres en los movimientos tengan un lote no leido
            update_sml_ids, lot_ids = self.reserve_free_lots(move, move_ids, lot_ids)
            # Devuelve un listado de moviemitnos y lotes que tendo que actualizar y o no tocar mas, ademas, lot_ids le ha quitado unidades
            sml_ids_to_update += update_sml_ids
            move_ids -= update_sml_ids
            #Si aun me quedan lotes ....
            if lot_ids and move_ids:
                msg = 'Error. No deberías de tener lotes y movimeintos'
                _logger.info (msg)
                raise (msg)

        if lot_ids and move.picking_type_id.allow_overprocess:
            _logger.info('-->> Creamos nuevos movimientos para los lotes %s' % lot_ids.mapped('name'))
            for lot_id in lot_ids:
                if move.quantity_done >= move.reserved_availability:
                    break
                reserved = move._update_reserved_quantity(1, 1, move.location_id, lot_id=lot_id, strict=False)
                if reserved:
                    sml_with_lot_ids += move.move_line_ids[-1]

        if sml_ids_to_update:
            self.update_sml_ids(move, sml_ids_to_update)


        return move

    def update_sml_ids(self, move, sml_ids_to_update):
        _logger.info('-->> Actualizo los movimientos con lotes: %s' % sml_ids_to_update.mapped('lot_id.name'))
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
        return

    @api.model
    def create_move_lots(self, vals):

        #PUNTO DE ENTRADA PARA CUANDO LLEGA DESDE LA PANTALLA DEL MOVIMEINTO DE LA APP
        _logger.info("#PUNTO DE ENTRADA PARA CUANDO LLEGA DESDE LA PANTALLA DEL MOVIMEINTO DE LA APP")

        move_id = vals.get('id', False)
        lot_names = vals.get('lot_names', False)
        if not lot_names:
            raise ValidationError("No has enviado ningún lote valido")
        move = self.browse(move_id)
        if not move:
            raise ValidationError("No has enviado ningún movimiento válido")
        if move.product_id.default_code in lot_names:
            raise ValidationError("Verifica que no has leido el codigo del producto")
        #Recupero la ubicación activa o la establezco por defecto
        active_location_id = vals.get('active_location', False)
        if lot_names:
            lot_ids = self.env['stock.production.lot']
            for lot in lot_names:
                lot_id = lot_ids.find_or_create_lot(lot.upper(), move.product_id, not move.picking_type_id.use_existing_lots)
                if lot_id:
                    lot_ids |= lot_id

        move.update_move_lot_apk(move, lot_ids, active_location=False)
        move._recompute_state()
        ## Devuelvo la información del moviemitno para ahorrar una llamada desde la apk

        if not move.picking_type_id.allow_overprocess and move.quantity_done > move.reserved_availability:
            raise ValidationError("No puedes procesar más cantidad de lo reservado para el movimiento")
        values = {'id': move.id, 'model': 'stock.move', 'view': 'form', 'filter_move_lines': vals.get('filter_move_lines', 'Todos')}
        return self.env['info.apk'].get_apk_object(values)
