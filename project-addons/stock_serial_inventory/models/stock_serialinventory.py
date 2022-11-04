# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils, float_compare

class SerialLineWzd(models.Model):
    _name = "serial.line.wzd"
    _description = "Serial x Line"
    _order = "name asc"

    line_id = fields.Many2one('stock.serial.inventory.line', string="Line")
    location_id = fields.Many2one(related="line_id.location_id")
    product_id = fields.Many2one(related="line_id.product_id")
    serial_id = fields.Many2one('stock.production.lot') ##, domain=[('real_location_id', '=', location_id), ('virtual_tracking', '=', True)])
    name = fields.Char(string='name')
    to_delete = fields.Boolean(string='To inventory adjust', default=False, help="If True, will be send to Inventory Location")
    
    _sql_constraints = [(
        'name_product_location_unique',
        'unique(name, line_id)',
        'This name is already used by another lot!'
        )]

    @api.onchange("name", 'location_id', 'product_id')
    def onchange_name(self):
        domain = [('name', '=', self.name), ('real_location_id', '=', self.location_id.id), ('product_id', '=', self.product_id.id)]
        self.serial_id = self.env['stock.production.lot'].search(domain, limit=1)

class SerialInventoryLine(models.Model):
    _name = "stock.serial.inventory.line"
    _description = "Serial Inventory Line"
    _order = "id desc"

    inventory_id = fields.Many2one("stock.serial.inventory", string="Serial Inventory")
    product_id = fields.Many2one("product.product", string="Product") ##, domain=[('virtual_tracking', '=', True)])
    serial_ids = fields.One2many('serial.line.wzd', 'line_id', string="Serials")
    location_id = fields.Many2one("stock.location", string="Location")
    location_dest_id = fields.Many2one("stock.location", string="Location Dest")

    def _get_move_values(self):
        
        inventory_id= self.inventory_id
        adjust_moves_to_action_done = moves_to_action_done = self.env['stock.move']
        for line in self:
            move_vals_dict = {}
            product_id = line.product_id
            stock_inventory = product_id.property_stock_inventory
            add_move = del_move = adjust_move = self.env['stock.move']
            ## CREO EL MOVIMIENTO
            move_vals_dict['adj_move'] = {
                        'name': _('INV_ADJ: ') + (inventory_id.name or ''),
                        'product_id': product_id.id,
                        'product_uom':product_id.uom_id.id,
                        'product_uom_qty': 0,
                        'date': inventory_id.date,
                        'company_id': inventory_id.company_id.id,
                        'serial_inventory_id': inventory_id.id,
                        'location_id': line.inventory_id.location_id.serial_location.id,
                        'location_dest_id': line.inventory_id.location_id.serial_location.id,
                        'state': 'done'}
            move_vals_dict['del_move'] = {
                        'name': _('INV_DEL:') + (inventory_id.name or ''),
                        'product_id': product_id.id,
                        'product_uom':product_id.uom_id.id,
                        'product_uom_qty': 0,
                        'date': inventory_id.date,
                        'company_id': inventory_id.company_id.id,
                        'serial_inventory_id': inventory_id.id,
                        'location_id': line.location_id.id,
                        'location_dest_id': stock_inventory.id,
                        'state': 'done',
                        'move_line_ids': [(0, 0, {
                            'product_id': product_id.id,
                            'product_uom_qty': 0,  # bypass reservation here
                            'product_uom_id': product_id.uom_id.id,
                            'qty_done': 0,
                            'location_id': line.location_id.id,
                            'location_dest_id': stock_inventory.id,
                        })]}
            move_vals_dict['add_move'] = {
                        'name': _('INV_ADD:') + (inventory_id.name or ''),
                        'product_id': product_id.id,
                        'product_uom':product_id.uom_id.id,
                        'product_uom_qty': 0,
                        'date': inventory_id.date,
                        'company_id': inventory_id.company_id.id,
                        'serial_inventory_id': inventory_id.id,
                        'location_id': stock_inventory.id,
                        'location_dest_id': line.location_id.id,
                        'state': 'done',
                        'move_line_ids': [(0, 0, {
                            'product_id': product_id.id,
                            'product_uom_qty': 0,  # bypass reservation here
                            'product_uom_id': product_id.uom_id.id,
                            'qty_done': 0,
                            'location_id': stock_inventory.id,
                            'location_dest_id': line.location_id.id,
                        })]}
            for serial in line.serial_ids:
                lot_id = serial.serial_id
                if not lot_id:
                    ## Lo tengo que buscar, y si lo hay lo actualizo
                    sql = "select id from stock_production_lot where name = '%s' and product_id = %d"%(serial.name, product_id.id)
                    self._cr.execute(sql)
                    res = self._cr.fetchall()
                    if res:
                        ## Lo tengo que actualizar.
                        ## Lo muevo a la ubicación de origen de la linea
                        lot_id = self.env['stock.production.lot'].browse(res[0])
                        if not lot_id.active:
                            lot_id.active = True
                        if lot_id.real_location_id != line.location_id:
                            move_line_vals = {
                                'product_id': product_id.id,
                                'product_uom_qty': 0,  # bypass reservation here
                                'product_uom_id': product_id.uom_id.id,
                                'qty_done': 0,
                                'location_id': lot_id.real_location_id.id,
                                'location_dest_id': line.location_id.id,
                                'serial_ids': [(4, lot_id.id)]
                            }
                            if not adjust_move:
                                adjust_move = self.env['stock.move'].create(move_vals_dict['adj_move'])
                            adjust_move.move_line_ids = [(0, 0, move_line_vals)]
                            if adjust_move not in adjust_moves_to_action_done:
                                adjust_moves_to_action_done |= adjust_move

                    ### si no lo hay, lo creo, pero solo si voy a añadirlo (si no ya no existe)
                    else:
                        if not serial.to_delete:
                            location_id = line.location_id.serial_location or line.location_id
                            vals = {
                                'name' : serial.name,
                                'ref' : serial.name,
                                'product_id': product_id.id,
                                'virtual_tracking': True,
                                'real_location_id': line.location_id.id,
                                'location_id': location_id.id,
                                'virtual_tracking': True,
                            }
                            lot_id = self.env['stock.production.lot'].create(vals)
                            
                            if not add_move:
                                add_move = self.env['stock.move'].create(move_vals_dict['add_move'])
                            add_move.move_line_ids.serial_ids = [(4, lot_id.id)]
                            if not add_move in moves_to_action_done:
                                moves_to_action_done |= add_move
                else:

                    ## Si ya está no hago nada
                    if not serial.to_delete and lot_id.real_location_id != line.location_id:
                        move_line_vals = {
                                'product_id': product_id.id,
                                'product_uom_qty': 0,  # bypass reservation here
                                'product_uom_id': product_id.uom_id.id,
                                'qty_done': 0,
                                'location_id': lot_id.real_location_id.id,
                                'location_dest_id': line.location_id.id,
                                'serial_ids': [(4, lot_id.id)]
                            }
                        if not adjust_move:
                            adjust_move = self.env['stock.move'].create(move_vals_dict['adj_move'])
                        adjust_move.move_line_ids = [(0, 0, move_line_vals)]
                        if adjust_move not in adjust_moves_to_action_done:
                            adjust_moves_to_action_done |= adjust_move

                        """
                        if not add_move:
                            add_move = self.env['stock.move'].create(move_vals_dict['add_move'])
                        add_move.move_line_ids.serial_ids = [(4, lot_id.id)]
                        if not add_move in moves_to_action_done:
                            moves_to_action_done |= add_move
                        """
                    if serial.to_delete and lot_id.real_location_id != stock_inventory:
                        if not del_move:
                            del_move = self.env['stock.move'].create(move_vals_dict['del_move'])
                        del_move.move_line_ids.serial_ids = [(4, lot_id.id)]
                        if del_move not in moves_to_action_done:
                            moves_to_action_done |= del_move

        if adjust_moves_to_action_done:
            for move in adjust_moves_to_action_done:
                move.move_line_ids.write({'qty_done': 0})
                move.write({'state': 'done'})
                move.move_line_ids.write_new_virtual_location()
        if moves_to_action_done:
            for move in moves_to_action_done:
                move.move_line_ids.write({'qty_done': 0})
                move.write({'state': 'done'})
                move.move_line_ids.write_new_virtual_location()
        return True
 
    @api.multi
    def open_serial_line_wzd(self):
        action = self.env.ref('stock_serial_inventory.action_stock_serial_line_wzd_tree').read()[0]
        action['domain'] = [('line_id', '=', self.id)]
        action['context'] = {
            'default_line_id': self.id,
            'default_location_id': self.location_id.id,
            'default_product_id': self.product_id.id,
            'default_inventory_id': self.id,
        }
        return action

    @api.multi
    def action_open_serial_mngt_line_wzd(self):
        vals = {'line_id': self.id}
        wzd_id = self.env['serial.mngt.wzd'].create(vals)
        action = self.env.ref('stock_serial_inventory.action_open_serial_mngt_line_wzd').read()[0]
        action['res_id'] = wzd_id.id
       
        return action

class SerialInventory(models.Model):
    _name = "stock.serial.inventory"
    _description = "Serial Inventory"
    _order = "date desc, id desc"

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))

    name = fields.Char(
        'Inventory Reference',
        readonly=True, required=True, default="/",
        states={'draft': [('readonly', False)]})
    date = fields.Datetime(
        'Inventory Date',
        readonly=True, required=True,
        default=fields.Datetime.now,
        help="If the inventory adjustment is not validated, date at which the theoritical quantities have been checked.\n"
             "If the inventory adjustment is validated, date at which the inventory adjustment has been validated.")
    line_ids = fields.One2many(
        'stock.serial.inventory.line', 'inventory_id', string='Inventories',
        copy=False, readonly=False,
        states={'done': [('readonly', True)]})
    move_ids = fields.One2many(
        'stock.move', 'serial_inventory_id', string='Created Moves',
        states={'done': [('readonly', True)]})
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        ('done', 'Validated')],
        copy=False, index=True, readonly=True,
        default='draft')
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, index=True, required=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('stock.inventory'))
    location_id = fields.Many2one(
        'stock.location', string="Inventory Location",
        readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        default=_default_location_id)
    product_id = fields.Many2one(
        'product.product', string="Inventoried Product",
        readonly=True,
        required=True,
        domain=[('virtual_tracking', '=', True)],
        states={'draft': [('readonly', False)]},
        help="Specify Product to focus your inventory on a particular Product.")
    inventory_id = fields.Many2one("stock.inventory", copy=False)
    update_quant_qty = fields.Boolean('Actualizar Cantidad')
    
    @api.model
    def create(self, vals):
        
        new_id = super().create(vals)
        if new_id.name == '/':
            new_id.name = "{} en {}: {}".format(new_id.product_id.default_code, new_id.location_id.name, new_id.date)
        return new_id


    @api.multi
    def unlink(self):
        for inventory in self:
            if inventory.state == 'done':
                raise UserError(_('You cannot delete a validated inventory adjustement.'))
        return super(SerialInventory, self).unlink()

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id.company_id:
            self.company_id = self.location_id.company_id

    def action_reset_product_qty(self):
        self.mapped('line_ids').write({'product_qty': 0})
        return True


    def action_validate(self):
        for line in self.line_ids:
            line._get_move_values()
        self.write({'state': 'done', 'date': fields.Datetime.now()})
        if self.update_quant_qty:
            self.action_validate_qty()
        return

    def action_check(self):
        """ Checks the inventory and computes the stock move to do """
        # tde todo: clean after _generate_moves
        for inventory in self.filtered(lambda x: x.state not in ('done','cancel')):
            # first remove the existing stock moves linked to this inventory
            inventory.with_context(prefetch_fields=False).mapped('move_ids').unlink()
            inventory.line_ids._generate_moves()

    def action_cancel_draft(self):
        self.mapped('move_ids')._action_cancel()
        self.write({
            'line_ids': [(5,)],
            'state': 'draft'
        })

    def action_start(self):
        
        for inventory in self.filtered(lambda x: x.state not in ('done','cancel')):
            inventory.create_inventory_lines()
            vals = {'state': 'confirm', 'date': fields.Datetime.now()}
            inventory.write(vals)

        return True

    def action_serial_inventory_line_tree(self):
        action = self.env.ref('stock_serial_inventory.action_serial_inventory_line_tree').read()[0]
        action['context'] = {
            'default_location_id': self.location_id.id,
            'default_product_id': self.product_id.id,
            'default_inventory_id': self.id,
        }
        return action

    def create_inventory_lines(self):
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location'].search([('id', 'child_of', self.location_id.id)])
        Product = self.env['product.product']
        Location = self.env['stock.location']
        SQ = self.env['stock.quant']
        # Empty recordset of products available in stock_quants
        quant_products = self.env['product.product']
        # Empty recordset of products to filter
        products_to_filter = self.env['product.product']
        if self.product_id:
            quant_domain = [('product_id', '=', self.product_id.id), ('location_id', 'child_of', self.location_id.id)]
        else:            
            quant_domain = [('location_id', 'child_of', self.location_id.id)]
        sq_ids = SQ.search(quant_domain)
        available_products = sq_ids.mapped('product_id')
        lot_domain = [('virtual_tracking', '=', True),('real_location_id', 'child_of', self.location_id.id)]
        if self.product_id:
            lot_domain += [('product_id', '=', self.product_id.id)]
        serial_ids = self.env['stock.production.lot'].search(lot_domain)
        line_vals = {'inventory_id', '=', self.id}
        lines = {}
        cont = len(serial_ids)
        for lot_id in serial_ids:
            cont -= 1
            line_id = self.env['stock.serial.inventory.line']
            real_location_id = lot_id.real_location_id.id
            product_id = lot_id.product_id.id
            if real_location_id in lines.keys():
                if product_id in lines[real_location_id].keys():
                    line_id = lines[real_location_id][product_id]
            if not line_id:
                line_vals = {
                    'inventory_id': self.id, 
                    'location_id': real_location_id, 
                    'product_id': product_id}
                line_id = self.env['stock.serial.inventory.line'].create(line_vals)
                if not real_location_id in lines.keys():
                    lines[real_location_id] = {}
                lines[real_location_id][product_id] = line_id
            line_id.serial_ids = [(0,0, {'line_id': line_id.id, 'name': lot_id.name, 'serial_id': lot_id.id, 'location_id': real_location_id})]
        if not self.line_ids:
            line_vals = {
                    'inventory_id': self.id, 
                    'location_id': self.location_id.id, 
                    'product_id': self.product_id.id}
            line_id = self.env['stock.serial.inventory.line'].create(line_vals)
        return True



    def action_validate_qty(self):

        ## creo un nuevo ajuste de inventario por cada línea 
        for line in self.line_ids:
            inventory_vals = {
                'name': 'From Serial %s in %s' % (line.product_id.default_code, line.location_id.name),
                'product_id': line.product_id.id,
                'location_id': line.location_id.id,
                'filter': 'product'
            }
            inv_id = self.env['stock.inventory'].create(inventory_vals)
            inv_id.action_start()
            line_id = inv_id.line_ids.filtered(lambda x: x.product_id == line.product_id and x.location_id == line.location_id)
            if line_id:
                line_id = line_id[0]
            if not line_id:
                line_vals = {
                    'inventory_id': inv_id.id,
                    'product_id': line.product_id.id,
                    'location_id': line.location_id.id}
                line_id = self.env['stock.inventory.line'].create(line_vals)
                line_id._onchange_product()
                line_id._onchange_quantity_context()
            domain = [('product_id', '=', line.product_id.id), ('real_location_id', '=', line.location_id.id)]
            product_qty = self.env['stock.production.lot'].search(domain, count=1)
            line_id.product_qty = product_qty
            
            inv_id.action_validate()
            self.inventory_id = inv_id
