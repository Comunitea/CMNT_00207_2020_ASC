# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from email.policy import default
import logging
from sqlite3 import Date

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

# from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)
PICK_GROUP_STATES = [('draft', 'Draft'), ('in_progress', 'In Progress'), ('picked', 'Picked')]
WEIGHT_LIMIT = 1000
VOLUME_LIMIT = 3
LINE_LIMIT = 1000
ITEM_LIMIT = 500
VOLUME_CTE = 1.25

class PickGroupLineBase(models.Model):
    _name = "pick.group.line"
    _description = "Pick Group Line"
    _order = "removal_priority desc"


class PickGroupLine(models.Model):

    _inherit = ["apk.model", "pick.group.line"]
    _name = "pick.group.line"
            
    @api.multi
    def set_picked(self):
        self.ensure_one()
        self.picked = not self.picked
        self.move_line_ids.write({'picked': self.picked})

     
    @api.multi
    def compute_difficulty(self):
        for line in self:
            line.volume = line.product_id.volume_factor / 100 * line.product_id.volume * line.qty
            line.weight = line.product_id.weight * line.qty
            line.nitems = line.qty
            line.nlines = len(line.move_line_ids)

    volume = fields.Float("Volumen", compute="compute_difficulty",digits=(16, 5))
    weight = fields.Float("Weight", compute="compute_difficulty")
    nlines = fields.Integer("Nº lines", compute="compute_difficulty")
    nitems = fields.Integer("Nº items", compute="compute_difficulty")

    group_id = fields.Many2one("pick.group", ondelete='cascade',)
    product_id = fields.Many2one('product.product', 'Product')
    location_id = fields.Many2one("stock.location", 'Location')
    location_dest_id = fields.Many2one("stock.location", 'Location')
    qty = fields.Float("Qty")
    picked = fields.Boolean("Picked")
    product_uom_id = fields.Many2one(related="product_id.uom_id")
    removal_priority = fields.Integer("Removal priority")
    move_line_ids = fields.One2many('stock.move.line', 'pick_group_line_id', 'Move lines')
    
    template_tracking = fields.Selection(related='product_id.template_tracking')

    @api.model
    def get_apk_tree(self, values):
        vals = []
        domain = values.get('domain', False)
        if not domain:
            raise ValidationError("_('Not domian for group lines")
        limit = values.get('limit', 0)
        offset = values.get('offset', 0)
        
        Moves = self.search(domain, limit=limit, offset=offset)
        if Moves:            
            picking_type_id = Moves[0].group_id.picking_type_id

        indice = 0
        group_id = {}
        for Move in Moves:
            Product = Move.product_id
            move_vals = {
                'id': Move.id,
                'name': Product.display_name,
                'product_id': Product and Product.get_apk_values()[0],
                'uom_id': {'id': Move.product_uom_id.id, 'name': Move.product_uom_id.name},
                'product_uom_qty': Move.qty,
                'qty_done': 0,
                'picked': Move.picked,
                'nlines': len(Move.move_line_ids),
                'weight': round(Move.weight, 2),
                'volume': round(Move.volume * 1000, 2),
                'picking_type_id': picking_type_id.id,
                'removal_priority': Move.removal_priority,
                'template_tracking': Move.template_tracking,
                'location_id': Move.location_id.get_def_values(),
                'location_dest_id': Move.location_dest_id.get_def_values(),
                'indice': indice
            }
            if not group_id:

                group_id = Move.group_id
                if not group_id.user_id:
                    group_id.user_id = self.env.user
                move_vals['group_id'] = group_id.get_apk_tree_values()
            indice += 1
            vals.append(move_vals)
            _logger.info("Valores para %s, %s"%(Move.id, Move.template_tracking))
        return vals

class PickGroupBase(models.Model):
    _name = "pick.group"
    _description = "Pick Group"

class PickGroup(models.Model):

    _inherit = ["apk.model", "pick.group"]
    _name = "pick.group"

    @api.multi
    def compute_difficulty(self):
        for group in self:
            volume = 0.0
            weight = 0.0
            lines = 0
            items = 0
            for line in group.line_ids:
                volume += line.volume
                weight += line.weight
                items += line.qty
                lines += 1
            group.volume = volume
            group.weight = weight
            group.nitems = items
            group.nlines = lines
    
    def write_picked(self, val=False):
        value = {'picked': val}
        self.batch_ids.mapped('move_line_ids').write(value)
        self.batch_ids.write(value)
        self.line_ids.write(value)

    @api.multi
    def run_picked(self):
        for group in self:
            group.write({'date_picked': fields.Datetime.now()})
            group.write_picked(True)
        # self.mapped('line_ids').write({'picked': True})
        return True
    
    @api.multi
    def picked_reset(self):
        for group_id in self:
            group_id.user_id = False
            group_id.date_picked = False
            self.write_picked(False)
        return True

    @api.multi
    @api.depends('line_ids.picked')
    def set_as_picked(self):
        for group in self:
            prev_state = group.state
            if all(x.picked for x in group.line_ids):
                group.state = "picked"
                if prev_state != "picked":
                    group.run_picked()
            elif all(not x.picked for x in group.line_ids):
                group.state = "draft"
            else:
                group.state = "in_progress"
    
    @api.multi
    @api.depends('batch_ids', 'batch_ids.picked')
    def compute_states(self):
        for group in self:
            if not group.batch_ids and not group.user_id:
                group.state = 'draft'
            else:
                if all(x.picked for x in group.batch_ids):
                    group.state = 'picked'
                else:
                    group.state = 'in_progress'

    @api.multi
    def compute_origin(self):
        for group_id in self:
            picks = group_id.mapped('batch_ids.picking_ids')
            
            if picks:
                origin = picks[0].origin
                for pick in picks[1:]:
                    origin = '%s\n%s'%(origin, pick.origin)
                group_id.origin = origin
            else:
                group_id = False


    @api.multi
    def _compute_order_ids(self):
        for group_id in self:
            group_id.sale_ids = group_id.mapped('batch_ids.sale_ids')
            group_id.purchase_ids = group_id.mapped('batch_ids.purchase_ids')
            group_id.picking_ids = group_id.mapped('batch_ids.picking_ids')
          
    sale_ids = fields.One2many('sale.order', string='Ventas', compute="_compute_order_ids")
    purchase_ids = fields.One2many('purchase.order', string='Compras', compute="_compute_order_ids")
    picking_ids = fields.One2many('stock.picking', string="Picking", compute="_compute_order_ids")
    state = fields.Selection(PICK_GROUP_STATES, default='draft', compute="compute_states", store=True)
    name = fields.Char("Name")
    date_picked = fields.Datetime("Picked Date")
    scheduled_date = fields.Datetime("Scheduled Date")
    user_id = fields.Many2one("res.users", "Picker")
    line_ids = fields.One2many("pick.group.line", "group_id", string="Lines")
    picking_type_id = fields.Many2one('stock.picking.type', 'Tipo')
    volume = fields.Float("Volume (l.)", compute="compute_difficulty", digits=(16, 5))
    weight = fields.Float("Weight (Kgrs.)", compute="compute_difficulty")
    nlines = fields.Integer("Nº lines", compute="compute_difficulty")
    nitems = fields.Integer("Nº items", compute="compute_difficulty")
    batch_ids = fields.One2many('stock.picking.batch', 'pick_group_id', 'Batchs')

    origin = fields.Text("Origin", compute="compute_origin")
    

    @api.model
    def button_picked_apk(self, vals):
        group_ids = self.browse(vals.get("id", False))
        if not group_ids:
            raise ValidationError("Pick Group not found")
        for group_id in group_ids:
            group_id.run_picked()
        return True

    def fill_with_batch(self, batch):
        _logger.info("Asign box para volumen %s"%batch.volume)
        to_box = batch.filtered(lambda x: not x.box_id)
        if to_box:
            to_box.assign_box_id()
        _logger.info("Asignado %s a %s"%(batch.box_id.display_name, batch.name))
        _logger.info("Creando las %d lineas agrupadas"%len(batch.move_line_ids))
        location_id = batch.picking_type_id.default_location
        for line in batch.move_line_ids:
            group_line = self.line_ids.filtered(lambda x: x.product_id == line.product_id and x[location_id] == line[location_id] and x.product_uom_id == line.product_uom_id)
            if group_line:
                group_line.qty += line.product_uom_qty
                line.pick_group_line_id = group_line
            else:
                vals = {
                    'group_id': self.id,
                    'product_id': line.product_id.id,
                    'location_id': line.location_id.id,
                    'location_dest_id': line.location_dest_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'picked': False,
                    'qty': line.product_uom_qty,
                    'removal_priority': line.location_id.removal_priority
                }
                pick_group_line_id = self.env['pick.group.line'].create(vals)
                line.pick_group_line_id = pick_group_line_id
        batch.pick_group_id = self
        _logger.info("Asignado %s "%batch.name)

    def continue_batching(self, batch_id=False):
        if not batch_id:
            if self.weight < WEIGHT_LIMIT:
                if self.volume < VOLUME_LIMIT:
                    if self.nlines < LINE_LIMIT:
                        if self.nitems < ITEM_LIMIT:
                            return True
        elif batch_id.move_line_ids:
            if self.weight + batch_id.weight <= WEIGHT_LIMIT:
                if self.volume + batch_id.volume <= VOLUME_LIMIT:
                    if self.nlines + batch_id.nlines <= LINE_LIMIT:
                        if self.nitems + batch_id.nitems <= ITEM_LIMIT:
                            return True
        return False

    def check_if_complete_for_products(self, product_ids, batch_ids):
        force_continue = False
        for batch in batch_ids:
            if self.continue_batching(batch):
                batch_product_ids = batch.mapped('move_line_ids.product_id')
                if all(x in product_ids for x in batch_product_ids):
                    _logger.info("Batch %s se completa"%batch.name)
                    self.fill_with_batch(batch)
                    # Si completo tengo que salir porque alguno anterior puede completarse con el añadido
                    force_continue = True
                    # Por lo tanto tengo que reiniciar el while con menos el batch
                    batch_ids -= batch
                    break
        return batch_ids, force_continue

    def force_assign(self, batch_ids):
        for batch in batch_ids:
            self.fill_with_batch(batch)
            
    def assign(self, batch_ids):
        if not self:
            domain = [('is_only_for_picking', '=', True)]
            type_id = self.env['stock.picking.type'].search(domain, limit=1)
            if not type_id:
                raise ValidationError(_("Not found type only for picking"))
            group_id = self.create({
                'name': type_id.sequence_id.next_by_id(),
                'picking_type_id': type_id.id
            })
        else:
            group_id = self[0]
        _logger.info("Grupo: %s" % group_id.name)
        _logger.info("Batchs: %s" % batch_ids.mapped('name'))
        batch_ids[0].pick_group_id = group_id
        batch = batch_ids[0]
        group_id.fill_with_batch(batch)
        batch_ids -= batch
        while group_id.continue_batching() and batch_ids:
            force_continue = False
            # Miro todos los batchs que si tienen productos y se llenan
            product_ids = group_id.mapped('line_ids.product_id')
            _logger.info("Buscando los que se cierran con los articulos en el grupo. Iteración n%d" % len(batch_ids))
            _logger.info("Articulos %s" % product_ids.mapped('default_code'))
            batch_ids, force_continue = group_id.check_if_complete_for_products(product_ids, batch_ids)
            if not batch_ids:
                break
            if force_continue:
                continue
            _logger.info("Añado nuevo batch")
            # Hay batchs pero no se complertan con artículo
            batch = batch_ids[0]
            if group_id.continue_batching(batch):
                group_id.fill_with_batch(batch)
                product_ids = group_id.mapped('line_ids.product_id')
                batch_ids -= batch
                batch_ids, force_continue = group_id.check_if_complete_for_products(product_ids, batch_ids)
            else:
                batch_ids -= batch
        return group_id
                        
    def get_filters(self):
        filters = [
            {'name': 'Estado', 'field': 'state'},
        ]
        return super().get_filters(filters)
    
    def get_apk_tree_values(self):
        self.ensure_one()
        vals = {}
        for Pick in self:
            # order_id = Pick.sale_id or Pick.purchase_id or False
            order_id = Pick.user_id or False
            partner_id = Pick.batch_ids.mapped('partner_id')
            partner_id = len(partner_id) == 1 and partner_id or False
            vals = {
                'id': Pick.id,
                'name': Pick.name,
                'user_id': {'id': Pick.user_id.id, 'name': Pick.user_id.name},
                'partner_id': partner_id and {'id': partner_id.id, 'name': partner_id.name},
                'order_id': order_id and {'id': order_id.id, 'name': order_id.name},
                'state': Pick.get_selection_dict_values('state', Pick.state),
                'nlines': Pick.nlines,
                'nitems': Pick.nitems,
                'volume': "{0:.2f}".format(Pick.volume * 1000),
                'weight': "{0:.2f}".format(Pick.weight), 
                'picking_ids': [{'id': pick.id, 'name': pick.name} for pick in Pick.picking_ids]
            }
        return vals