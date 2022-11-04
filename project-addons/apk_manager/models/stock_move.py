from odoo import api, fields, models, _
#from pprint import pprint
from .apk_manager import LIMIT
import logging
_logger = logging.getLogger(__name__)
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError


class StockMove(models.Model):
    _inherit = ["apk.model", "stock.move"]
    _name = "stock.move"


    @api.model
    def action_assign_apk(self, values):
        move_id = self.browse(values['move_id'])
        if not move_id:
            raise ValidationError('No se ha encontrado un movimiento')
        return move_id._action_assign_apk(values)
    
    def _action_assign_apk(self, values):
       
        lot_id = values.get('lot_id', False)
        # #Si ya hay cantidaes hechas no debería de borrar ese movimiento. Por lo tanto, voy a probar dejando ...
        # # ESTO ES IMPORTANTE NO DEBERÍA DE DEJAR RESERVAR LAS CANTIDADES YA HECHAS
        self.move_line_ids.filtered(lambda x: x.qty_done == 0).unlink()
        for sml in self.move_line_ids:
            # # Cambio la reserva a los movientos hechos
            sml.product_uom_qty = sml.qty_done
        
        # # Recalculo el estado del movimiento
        self._recompute_state()

        # # Si tengo un lote, fuerzo la reserva con el lote
        ctx = self._context.copy()
        if lot_id:
            ctx.update(force_lot_id=lot_id)
        self.with_context(ctx)._action_assign()
        _logger.info("Se ha cambiado la reserva en moviento {} al lote {}".format(self.name, lot_id))
        return self.move_line_ids.get_apk_tree_values()
    
    def _update_reserved_quantity(self, need, available_quantity,
                                  location_id, lot_id=None,
                                  package_id=None, owner_id=None,
                                  strict=True):
        if self._context.get('force_lot_id'):
            lot_id = self.env['stock.production.lot'].browse(self._context['force_lot_id'])
        return super()._update_reserved_quantity(
            need, available_quantity, location_id, lot_id=lot_id,
            package_id=package_id, owner_id=owner_id, strict=strict)

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        if self._context.get('force_quant', False):
            reserved_quant = self._context.get('force_quant', None)
        vals = super(StockMove, self)._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        if self.picking_type_id.app_integrated:
            vals.update({
               'need_location_id': self.picking_type_id.need_location_id,
               'need_location_dest_id': self.picking_type_id.need_location_dest_id,
               'need_confirm_lot_id': self.picking_type_id.need_confirm_lot_id,
               'need_confirm_product_id': self.picking_type_id.need_confirm_product_id,
               'need_loc_before_qty': self.picking_type_id.need_loc_before_qty,
            })
        if self.product_id.tracking == 'none':
            vals['need_confirm_lot_id'] = False
        else:
            vals['need_confirm_lot_id'] = self.picking_type_id.need_confirm_lot_id
        if self.picking_id.batch_id.box_id:
            vals.update({'location_dest_id': self.picking_id.batch_id.box_id.id})

        return vals

    def assign_removal_priority(self, location_dest_id=False, field='', field_dest=''):
        return self.move_line_ids.assign_removal_priority(location_dest_id=location_dest_id, field=field, field_dest=field_dest)