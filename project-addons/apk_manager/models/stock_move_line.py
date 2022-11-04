from odoo import api, fields, models, _
#from pprint import pprint
from .apk_manager import LIMIT
import logging
from pygments.lexer import inherit
_logger = logging.getLogger(__name__)
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

class StockMoveLine(models.Model):
    _inherit = ["apk.model", "stock.move.line"]
    _name = "stock.move.line"
    _order = "removal_priority desc, removal_dest_priority, product_id"


    @api.multi
    def _compute_apk_state(self):
        for move in self:
            move.apk_state = move.state
            if move.apk_state == 'done' and move.qty_done == move.product_uom_qty:
                move.apk_state = 'picked'
            elif move.apk_state in ('partially_available', 'assigned') and move.qty_done > 0:
                move.apk_state = 'in_progress'


    box_id = fields.Many2one(related="picking_id.box_id", string="Box")
    apk_state = fields.Selection([
        ('cancel', 'Cancelado'),
        ('draft', 'No disponible'),
        ('confirmed', 'Confirmado'),
        ('waiting', 'En espera'),
        ('in_progress', 'En proceso'),
        ('partially_available', 'Parcial'),
        ('picked', 'Picked'),
        ('assigned', 'Completado'),
        ('done', 'Validado')], compute='_compute_apk_state')

    # tracking = fields.Selection(related="move_id.tracking")
    # picking_type_id = fields.Many2one(related="move_id.picking_type_id")
    removal_priority = fields.Integer(string="Removal priority")
    removal_dest_priority = fields.Integer(string="Removal dest priority")
    filterqties = fields.Selection( [
        ('0', 'Pendientes'),
        ('1', 'En proceso'),
        ('2', 'Pick Completo'),
        # ('3', 'Pick + Ubicación'),
        ], store=False)
    need_location_dest_id = fields.Boolean('Apk confirma destino', copy=False, help="Si está marcado, la aplicación necesitará confimar destino para cada movimiento")
    need_location_id = fields.Boolean('Apk confirma origen', copy=False, help="Si está marcado, la aplicación necesitará confimar origen para cada movimiento")
    need_confirm_lot_id = fields.Boolean('Apk confirma lote', copy=False, help="Si está marcado, la aplicación necesitará confimar el lote para cada movimiento")
    need_confirm_product_id = fields.Boolean('Apk confirma producto', copy=False, help="Si está marcado, la aplicación necesitará confimar el lote para cada movimiento")
    need_loc_before_qty = fields.Boolean('Apk confirma ubic antes qty', copy=False, help="Si está marcado, la aplicación necesitará confimar ubicaciones antes de cantidades")
    

    @api.model
    def search(self, dom, offset=0, limit=None, order=None, count=False):
        ## print ('Search read: CONTEXTO:\n %s\n y DOMINIO\n%s'%(self._context, dom))
        if self._context.get('from_pda', False) and len(dom) > 1:
            ctx = self._context.copy()
            ctx.update(from_pda=False)
            new_dom = []
            filter_qties_domain = []
            for arg in dom:
                if arg[0] != 'filterqties':
                    new_dom += [arg]
                else:
                    filter_qties_domain = arg
            fields = ['id', 'product_uom_qty', 'qty_done', 'need_location_id', 'need_location_dest_id']
            res = self.with_context(ctx).search_read(new_dom, fields)
            qties_domain = []

            if filter_qties_domain:
                options = filter_qties_domain[2]
                for option in options:
                    if option == '0':
                        option_domain = [('qty_done', '=', 0)]
                        ## dom.insert(k, ('qty_done', '=', 0))
                        # dom.insert(k, ('id', 'in', ids))
                    elif option == '1':
                        ## ids = [x['id'] for x in res if x['qty_done'] < x['product_uom_qty']]
                        ids = [x['id'] for x in res if (x['need_location_id'] or x['need_location_dest_id'] or x['qty_done'] < x['product_uom_qty']) ]
                        option_domain = [('id', 'in', ids)]
                        #dom.insert(k, ('id', 'in', ids))
                    elif option == '2':
                        ## ids = [x['id'] for x in res if x['qty_done'] >= x['product_uom_qty']]
                        ids = [x['id'] for x in res if (not x['need_location_id'] and not x['need_location_dest_id'] and x['qty_done'] >= x['product_uom_qty'])]
                        option_domain = [('id', 'in', ids)]

                    if qties_domain:
                        qties_domain = expression.OR([qties_domain, option_domain])
                    else:
                        qties_domain = option_domain

            if qties_domain:
                qties_domain = expression.OR([qties_domain])
                dom = expression.AND([qties_domain, new_dom])
        return super().search(dom, offset=offset,
                                              limit=limit, order=order,
                                              count=count)

    def get_textarea_lot_ids(self):
        text = ''
        for lot in self.serial_ids:
            text += "%s\n" % lot.name
        return text

    def inc_qty_done_by_1(self, allow_overprocess):
        if not allow_overprocess and (1 + self.qty_done) > self.product_uom_qty:
            raise ValidationError('No puedes procesar más cantidad que la pedida (%s)'%self.product_uom_qty)
        self.qty_done += 1

    def get_apk_tree_values(self):
        vals = []
        # import ipdb; ipdb.set_trace()
        for Move in self:
            Pick = Move.picking_id
            # order_id = Pick.sale_id or Pick.purchase_id or False
            # order_id = order_id and {'id': order_id.id, 'name': order_id.name} or False
            Batch = Pick.batch_id
            Product = Move.product_id
            box_id = Move.location_dest_id
            ChangeQty = not (Move['need_location_id'] or Move['need_confirm_product_id'])
            serial_ids = Move.serial_ids.sorted('name')
            if Move.picking_type_id.use_create_lots:
                serial_ids = Move.serial_name_ids.sorted('name')
            else:
                serial_ids = Move.serial_ids.sorted('name')
            serials = serial_ids.sorted('name').mapped('name')
            move_vals = {
                'id': Move.id,
                'ChangeQty': ChangeQty,
                'picking_id': Pick and {'id': Pick.id, 'name': Pick.name} or False,
                'batch_id': Batch and {'id': Batch.id, 'name': Batch.name} or False,
                'name': Product.default_code,
                'product_id': Product and Product.get_apk_values()[0],
                'uom_id': {'id': Move.move_id.product_uom.id, 'name': Move.move_id.product_uom.name},
                'product_uom_qty': Move.product_uom_qty,
                'qty_done': Move.qty_done,
                'state': Move.get_selection_dict_values('apk_state', Move.apk_state),
                'box_id': box_id.get_def_values() or False,
                'sml_count': 1,
                'from_list': True,
                'picking_type_id': Move.picking_type_id and Move.picking_type_id.id,
                'move_id': Move.move_id.id,
                'picking_id': Move.picking_id and {'id': Move.picking_id.id, 'name': Move.picking_id.name} or False,
                'removal_priority': Move.removal_priority,
                'template_tracking': Move.template_tracking,
                'location_id': Move.location_id.get_def_values(),
                'location_dest_id': Move.location_dest_id.get_def_values(),
                'need_loc_before_qty': Move.need_loc_before_qty,
                'need_location_id': Move.need_location_id,
                'need_location_dest_id': Move.need_location_dest_id,
                'need_confirm_lot_id': Move.need_confirm_lot_id,
                'need_confirm_product_id': Move.need_confirm_product_id,
                'lot_id' : Move.lot_id and Move.lot_id.get_def_values() or False,
                'serial_ids' : serial_ids and [lot_id.get_def_values() for lot_id in serial_ids] or [],
                'serials': serials,
                'lot_name': Move.lot_name,
            }
            forbidden = [x.name for x in Product.not_lot_name_ids]
            if forbidden:
                move_vals['forbidden'] = forbidden
            # Si pasa esto, el movimiento se puede hacer desde el listado de movimientos
            vals.append(move_vals)
            # _logger.info("Valores para %s, %s"%(Move.id, Move.template_tracking))
        return vals

    def get_related_locs(self):
        if not self:
            return []
        Picks = self.mapped('picking_id')
        location_ids = self.env['stock.location']
        if Picks:
            location_ids |= Picks.mapped('location_id')
            location_ids |= Picks.mapped('location_dest_id')
        loc_domain = [('location_id', 'child_of', location_ids[0].id)]
        for loc in location_ids[1:]:
            loc_domain = ['|'] + loc_domain + [('location_id', 'child_of', loc.id)]
        Res_Locs = {}
        for loc in self.env['stock.location'].search_read(loc_domain, ['id', 'name', 'barcode']):
            barcode = loc['barcode'] or loc['name']
            Res_Locs[barcode] = {'id': loc['id'], 'name': loc['name']}
        return Res_Locs


    @api.model
    def get_apk_tree(self, values):

        batch_id = values.get('batch_id', False)
        state = values.get('state', False)
        model = 'stock.move.line' ## values.get('model', 'stock.picking.batch')
        limit = values.get('limit', LIMIT)
        offset = values.get('offset', 0)
        domain = values.get('domain', False)
        only_moves = values.get('only_moves', True)
        if domain:
            domain = domain
        else:
            domain = []
        if batch_id:
            ## Para no hacer el campo store, voy a probar así ....
            domain += [('picking_id.batch_id', '=', batch_id)]
        if state:
            domain += [('state', '=', state)]

        order = 'removal_priority asc, product_id, picking_id'
        Moves = self.search(domain, limit=limit, order=order, offset=offset)
        res = Moves.get_apk_tree_values()
        if only_moves:
            return {'Moves': res}

        Filters = Moves and Moves.get_filters() or []
        Type = Moves and Moves[0].picking_type_id.get_apk_values() or {}
        Locs = Moves.get_related_locs()
        vals = {'Moves': res, 'Filter': Filters, 'Type': Type, 'Locs': Locs}
        return vals

    @api.model
    def create_new_lot(self, values):

        sml_id = self.browse(values['move_id'])
        product_id = self.env['product.product'].browse(values['product_id'])
        lot_name = values.get('lot_name', False)

        ## Miro si existe el lote
        lot_domain = [('product_id', '=', values['product_id']), ('name', '=', lot_name), '|', ('active', '=', True), ('active', '=', False)]
        lot_id = self.env['stock.production.lot'].search(lot_domain)
        # Si está desactivado lo activo:
        if lot_id:
            if not lot_id.active:
                lot_id.active = True

        if not lot_id:
            lot_vals = {
                'name': lot_name,
                'ref': lot_name,
                'location': sml_id.picking_id.location_id.id,
                'product_id': product_id.id,
                'virtual_tracking': product_id.virtual_tracking}
            lot_id = self.env['stock.production.lot'].create(lot_vals)

        if not sml_id.lot_id:
            sml_id.lot_id = lot_id
            return {'NewId': sml_id.id}
        ## Tengo que crear uno nuevo ....
        new_sml_id = sml_id.copy()
        new_sml_id.write({
            'lot_id': lot_id.id,
            'qty_done': 0
            })

        return {'NewId': new_sml_id.id}


    @api.model
    def reset_moves(self, values):
        sml_ids = self.browse(values['ids'])
        sml_ids.write(values['values'])
        sml_ids.serial_name_ids.unlink()
        sml_ids.write({'lot_ids_string': ""})
        return True

    def get_filters(self):
        def return_filter(field):
            if self.fields_get()[field]["type"] == "selection":
                res = self.get_selection_dict_values(field)
            return res
        filters = [
            {'name':'Estado', 'field': 'state'},
            {'name': 'Cantidades', 'field': 'filterqties'}
            # {'name':'Prioridad', 'field': 'priority'},
            # {'name':'Transportista', 'field': 'carrier_id'},
        ]
        filters = super().get_filters(filters)
        for f in filters:
            if f['field'] == 'filterqties':
                f['values'] = return_filter(f['field'])
        ## COmo el campo filterqties no se guarda lo fuerzo
        ## con todos los valores
        return filters

    @api.model
    def update_loc(self, values):
        
        sml_id = values.get('sml_id', False)
        barcode = values.get('barcode', False)
        loc_id = self.env['stock.location']
        field = values.get('location', 'location_id')
        if barcode:
            domain = [('barcode', '=', barcode)]
            loc_id = self.env['stock.location'].search(domain, limit=1)
        if not loc_id:
            raise ValidationError('No se ha encontrado el código %s'%barcode)
        sml_id = self.env['stock.move.line'].browse(sml_id)
        sml_id[field] = loc_id
        if field == 'location_dest_id':
            sml_id.box_id = loc_id
        move_id = sml_id.move_id
        val = move_id.move_line_ids.get_apk_tree_values()
        return val
    
    @api.model
    def load_multi_serials(self, values):
        return self.add_virtual_serial(values)
        
    @api.model
    def add_virtual_serial(self, values):
        move_id = self or self.browse(values['id'])
        to_delete = values.get('to_delete', False)
        serial_names = values.get('serial_names', [])
        if serial_names:
            serial_names = move_id.compute_names_from_string(serial_names)
        if not serial_names:
            return {'error': 'Has leido códigos invalidos %s' % values.get('serial_names', []), 'move': False}

        if 'use_create_lots' in values:
            use_create_lots = values['use_create_lots']
        else:
            use_create_lots = move_id.picking_type_id and move_id.picking_type_id.use_create_lots
        
        VPL = self.env['virtual.serial']
        if to_delete:
            if use_create_lots:
                ## Se hace con serial_name_ids
                domain = [('move_line_id', '=', move_id.id), ('name', 'in', serial_names)]
                serial_name_ids = VPL.search(domain)
                serial_name_ids.unlink()
                move_id.qty_done = len(move_id.serial_name_ids)
            else:
                delete = move_id.serial_ids.filtered(lambda x: x.name in serial_names)
                move_id.write({'serial_ids': [(3, x.id) for x in delete]})
                move_id.qty_done = len(move_id.serial_ids) 
            ## res = {'error': False, 'move': move_id.get_apk_tree_values()[0]}
        elif use_create_lots:
            ## Tengo que usar solo los que ya están virtual.production.lot
            domain = [('move_line_id', '=', move_id.id), ('name', 'in', serial_names)]
            serial_name_ids = VPL.search(domain)
            lot_names = serial_name_ids.mapped('name')
            for name in serial_names:
                if name not in lot_names:
                    values = {'name': name, 'move_line_id': move_id.id}
                    VPL.create(values)
            ## move_id.lot_ids_string = ','.join(move_id.serial_name_ids.mapped('name'))
            move_id.qty_done = len(move_id.serial_name_ids)
            #res = {'error': False, 'move': move_id.get_apk_tree_values()[0]}
        else:
            SPL = self.env['stock.production.lot']
            serial_location_id = move_id.location_id.serial_location
            domain = move_id.product_id.get_serial_domain(serial_location_id, lot_names=serial_names)
            #domain = [
            #    ('product_id', 'in', product_id.get_subproduct().ids), 
            #    ('name', 'in', serial_names), 
            #    ('location_id', 'child_of', serial_location_id.id),
            #    '|',('active', '=', True), ('active', '=', False)]
            serial_ids = SPL.search(domain)
            if any(x not in serial_ids.mapped('name') for x in serial_names):
                res = {'error': 'Error en los nº: %s. Comprueba si existen en la ubicación'%','.join(serial_names), 'move': False}
                return res
            ## Puedo añadir todos, y ya existen
            move_id.write({'serial_ids': [(4, x.id) for x in serial_ids]})
            move_id.qty_done = len(move_id.serial_ids)

        res = {'error': False, 'move': move_id.get_apk_tree_values()[0]}
        return res
            

    @api.model
    def add_set_lot(self, values):
        move_id = self.browse(values['id'])
        if move_id.need_confirm_product_id:
            raise ValidationError("Debes ler primero el proucto")
        use_create_lots = move_id.picking_type_id and move_id.picking_type_id.use_create_lots
        allow_overprocess = move_id.picking_type_id and move_id.picking_type_id.allow_overprocess
        need_confirm_lot_id = move_id.need_confirm_lot_id
        
        lot_name = values.get('lot_name', '')
        if not lot_name:
            return
        if use_create_lots:
            move_id_lot_name = move_id.lot_id and move_id.lot_id.name or move_id.lot_name 
            if move_id_lot_name == lot_name:
                if move_id.template_tracking == 'lot':
                    if not move_id.need_confirm_lot_id:
                        move_id.qty_done += 1
                    else:
                        move_id.need_confirm_lot_id = False
                if move_id.template_tracking == 'serial':
                    move_id.qty_done = 1
            else:
                ## Si se cambia y la cantidad no es 0 error
                if move_id_lot_name:
                    if move_id.qty_done > 0:
                        raise ValidationError(_('Qty done must be 0, to change lot/serial'))
                    ## Si lo cambio tengo que confirmarlo siempre
                    move_id.need_confirm_lot_id = True
                else:
                    move_id.need_confirm_lot_id = False
                ## Si tiene lot_id, lo pongo a cero, y escribo lot_name
                if move_id.lot_id:
                    ## Establezco el lote
                    lot_domain = [('product_id', '=', move_id.product_id.id), ('name', '=', lot_name)]
                    move_id.lot_id = self.env['stock.production.lot'].search(lot_domain, limit = 1)
                move_id.lot_name = lot_name
                move_id.qty_done = 0
        else:
            ## Solo lotes existentes
            if move_id.lot_id.name == lot_name:
                if move_id.template_tracking == 'lot':
                    if not move_id.need_confirm_lot_id:
                        move_id.qty_done += 1
                    else:
                        move_id.need_confirm_lot_id = False
                    if not allow_overprocess and move_id.product_uom_qty < move_id.qty_done:
                        raise ValidationError(_('Not over process allowed'))
                elif move_id.template_tracking == 'serial':
                    if move_id.need_confirm_lot_id:
                        move_id.need_confirm_lot_id = False
                    else:
                        move_id.qty_done = 1
                ## return {'move': False, 'lot_id': move_id.lot_id.get_def_values(), 'serials': [move_id.lot_name], 'qty_done': move_id.qty_done}
            else:
                ## Se cambia el lote
                if move_id.lot_id and move_id.qty_done > 0:
                    raise ValidationError(_('Qty done must be 0, to change lot/serial'))
                lot_domain = [('product_id', '=', move_id.product_id.id), ('name', '=', lot_name)]
                lot_id = self.env['stock.production.lot'].search(lot_domain, limit = 1)
                if not lot_id:
                    raise ValidationError (_('Not found: %s'% lot_name))
                ## TODO: TENGO QUE REVISAR ESTO
                move_id.lot_id = lot_id
                move_id.qty_done = 0
                move_id.need_confirm_lot_id = move_id.picking_type_id and move_id.picking_type_id.need_confirm_lot_id or False
        res = {'move': move_id.get_apk_tree_values()[0]}
        return res

    @api.model
    def action_assign_apk(self, values):
        ## Action assign desde la apk
        ## También se usa para obligar a asignar lotes
        ##return self.add_lot_name(values)
        move_line_id = self.browse(values['move_id'])
        values.update(move_id=move_line_id.move_id.id)
        move_id = move_line_id.move_id
        values.update(move_id=move_line_id.move_id.id)
        return move_id.action_assign_apk(values)
    """
    @api.model
    def add_move_line(self, values):
        ## AÑADIMOS UN NUEVO STOCK MOVE LINE A UN MOVIMINETO ### 
        id = values.get('id')
        sml_id = self.browse(id)
        product_uom_qty = sml_id.product_uom_qty - sml_id.qty_done
        sml_id.product_uom_qty = sml_id.qty_done

        sml_id.move_id.state = 'partially_available'
        sml_id.move_id._action_assign()
        new_sml_id = sml_id.move_id.move_line_ids.filtered(lambda x: x.id != id and x.qty_done == 0)
        if new_sml_id:
            return new_sml_id.get_apk_tree_values()
        else:
            return sml_id.get_apk_tree_values()

    """
    @api.model
    def update_sml_id_lot(self, lot_name):
        ## SOLO DEBERÍA DE LLEGAR 1 LOTE EN LOT_NAME
        ## CASO 1. STOCK_MOVE_LINE NO TIENE LOTE
        
        domain = [('product_id', '=', self.product_id.id), ('name', '=', lot_name), ('virtual_tracking', '=', False)]
        lot_id = self.env['stock.production.lot'].search(domain, limit=1)

        ## Si no hay un lote lo creo
        if not lot_id:
            if not self.picking_type_id.use_create_lots:
                raise ValidationError (_('No puedes crear lotes en este tipo'))
            vals = {'name': lot_name, 'product_id': self.product_id.id, 'ref': lot_name}
            lot_id = self.env['stock.production.lot'].create(vals)
        ## Si el movimiento no tiene lo te o la cantidad hecha es 0, lo cambio
        if not self.lot_id or not self.qty_done:
            if self.lot_id != lot_id:
                self.qty_done = 0
            self.lot_id = lot_id
        ## Si tiene lote y la cantidad está hecha, entonces tengo que crear uno nuevo
        elif self.lot_id and self.qty_done:
            new_move = self.copy({'lot_id':lot_id.id, 'qty_done':0})
            self = new_move
        return self.get_apk_tree_values()

    @api.multi
    def write(self, vals):
        return super().write(vals)

    @api.model
    def action_copy_line(self, values):
        sml_id = self.browse(values['id'])
        return sml_id._action_copy_line(values)
    
    def _action_copy_line(self, values):
        move_id = self.move_id
        ## En principio, haremos un movimiento por la cantidad que falte por hacer
        move_id.move_line_ids.filtered(lambda x: x.qty_done == 0).unlink()
        for sml_id in move_id.move_line_ids:
            sml_id.product_uom_qty = sml_id.qty_done
        move_id._recompute_state()
        box_id = move_id.picking_id.box_id
        batch_id = move_id.picking_id.batch_id
        ctx = self._context.copy()
        if move_id.template_tracking != 'none':
            ctx.update(not_lot_id = move_id.move_line_ids.mapped('lot_id'))
        else:
            ctx.update(not_loc_id = move_id.move_line_ids.mapped('location_id'))
        move_id.with_context(ctx)._action_assign()
        new_move_lines = move_id.move_line_ids.filtered(lambda x:not x.qty_done)
        for sml_id in new_move_lines:
            sml_id.location_dest_id = box_id
            sml_id.batch_id = batch_id
        new_move_lines.assign_removal_priority()


        return move_id.move_line_ids.get_apk_tree_values()


    def assign_removal_priority(self, location_dest_id = False, field='', field_dest=''):
        if not self:
            return
        line = self[0]
        if not field:
            field = line.picking_type_id.default_location or 'location_id'
            if field == "location_id":
                field_dest = "location_dest_id"
            else:
                field_dest = "location_id"
        move_line_location_id = line[field]
        for move_line in self:
            if location_dest_id:
                move_line.location_dest_id = location_dest_id
            move_line.removal_priority = move_line[field].removal_priority
            move_line_location_id = move_line[field]
            move_line.removal_dest_priority = move_line[field_dest].removal_priority
            self.move_line_location_id = move_line_location_id
            ## self._compute_track_from_product()