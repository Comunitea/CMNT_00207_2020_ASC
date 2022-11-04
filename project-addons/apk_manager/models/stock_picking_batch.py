from odoo import api, fields, models, _
#from pprint import pprint
from .apk_manager import LIMIT
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp
# import threading
import logging
_logger = logging.getLogger(__name__)

class StockPickingBatch(models.Model):

    _inherit = ["apk.model", "stock.picking.batch"]
    _name = "stock.picking.batch"

    @api.multi
    def compute_move_line_count(self):
        for pick in self:
            pick.move_line_count = len(pick.move_line_ids)

    @api.multi
    def is_delayed(self):
        picking_ids = self.filtered(lambda x: x.state != 'done' and x.date < fields.datetime.today())
        picking_ids.write({'delayed': True})

    @api.multi
    @api.depends('picking_ids', 'partner_id', 'name', 'sale_ids', 'purchase_ids')
    def compute_search_str(self):
        for batch in self:
            search_str = batch.name
            if batch.partner_id:
                search_str = '%s-%s' % (search_str, batch.partner_id.display_name)
            for pick in batch.picking_ids:
                search_str = '%s-%s' % (search_str, pick.name)
            for sale in batch.sale_ids:
                search_str = '%s-%s' % (search_str, sale.name)
            for purchase in batch.purchase_ids:
                search_str = '%s-%s' % (search_str, purchase.name)
                if purchase.partner_ref:
                    search_str = '%s-%s' % (search_str, purchase.partner_ref)
            
            batch.search_str = search_str

    @api.multi
    def compute_difficulty(self):
        for batch in self:
            volume = 0.0
            weight = 0.0
            lines = 0
            items = 0
            for line in batch.move_line_ids:
                volume += 1.25 * line.product_id.volume * line.product_uom_qty
                weight += 1.25 * line.product_id.weight * line.product_uom_qty
                items += line.product_uom_qty
                lines += 1
            batch.volume = volume
            batch.weight = weight
            batch.nitems = items
            batch.nlines = lines

    volume = fields.Float("Volumen", compute="compute_difficulty", digits=(16,5))
    weight = fields.Float("Weight", compute="compute_difficulty")
    nlines = fields.Integer("Nº lines", compute="compute_difficulty")
    nitems = fields.Integer("Nº items", compute="compute_difficulty")
    

    # move_line_grouped_count = fields.Integer (compute="_get_move_line_grouped_count")
    delayed = fields.Boolean('Delayed', compute=is_delayed)
    box_id = fields.Many2one(
        "stock.location", "Box", domain=[("is_box", "=", True)]
    )
    try_validate = fields.Boolean("Validación desde PDA", default=False)
    move_line_count = fields.Integer("# Operaciones", compute="compute_move_line_count")
    partner_id = fields.Many2one(related="picking_ids.partner_id")
    carrier_id = fields.Many2one(related="picking_ids.carrier_id")
    scheduled_date = fields.Date(related="date")
    # picking_type_id = fields.Many2one('stock.picking.type', string="Tipo de albarán")
    needed_space = fields.Float("Required vol in box", compute="compute_needed_space_in_box")
    search_str = fields.Char("Cadena de busqueda en APK", compute="compute_search_str", store=True)

    @api.onchange('box_id')
    def onchange_box_id(self):
        box_id = self.box_id or self.picking_type_id.default_location_dest_id or self.env['stock.location']
        if box_id:
            self.move_line_ids.write({'location_dest_id': box_id.id})
            # self.picking_ids.write({'location_dest_id': box_id.id})

    @api.model
    def get_apk_info(self, values):
        batch_id = values.get('id', False)
        batch_id = self.browse(batch_id)
        vals = {
            'name': batch_id.name,
            'state': batch_id.state,
            'team_id': batch_id.team_id and {'id': batch_id.team_id.id, 'name': batch_id.team_id.name, 'wh_code': batch_id.team_id.wh_code} or False,
            'carrier_id': batch_id.carrier_id and {'id': batch_id.carrier_id.id, 'name': batch_id.carrier_id.name, 'wh_code': batch_id.carrier_id.wh_code} or False,
            'carrier_weight': batch_id.carrier_weight,
            'carrier_packages': batch_id.carrier_packages,
            'notas': batch_id.notes,
            'box_id': batch_id.box_id and {'id': batch_id.box_id.id, 'name': batch_id.box_id.name} or False,
            'weight': batch_id.weight,
            'volume': batch_id.volume,
            'nlines': batch_id.nlines,
            'nitems': batch_id.nitems,
            'try_validate': batch_id.try_validate,
            'picking_type_id': batch_id.picking_type_id.id

        }
        if batch_id.carrier_id:
            vals['carrier'] = batch_id.carrier_id.display_name
            vals['carrier_code'] = batch_id.carrier_id.code
        if batch_id.picking_ids:
            vals['picking_ids'] = ','.join(batch_id.mapped('picking_ids.name')),
        if batch_id.sale_ids:
            vals['sale_ids'] = ','.join(batch_id.mapped('sale_ids.name')),
        if batch_id.purchase_ids:
            vals['purchase_ids'] = ','.join(batch_id.mapped('purchase_ids.name')),
        return vals

    def reset_try_validate(self):
        self.write({'try_validate': False})

    def get_apk_tree_values(self):
        self.ensure_one() ## ?????
        for Pick in self:
            # order_id = Pick.sale_id or Pick.purchase_id or False
            vals = {
                'id': Pick.id,
                'name': Pick.apk_name or Pick.name,
                'state': Pick.get_selection_dict_values('state', Pick.state),
                'nlines': Pick.nlines,
                'nitems': Pick.nitems,
                'team_id': Pick.team_id and {'id': Pick.team_id.id, 'name': Pick.team_id.name, 'wh_code': Pick.team_id.wh_code} or False,
                'carrier_id': Pick.carrier_id and {'id': Pick.carrier_id.id, 'name': Pick.carrier_id.name, 'wh_code': Pick.carrier_id.wh_code} or False,
                'volume': "{0:.2f}".format(Pick.volume),
                'weight': "{0:.2f}".format(Pick.weight),
                'picked': Pick.picked,
                'try_validate': Pick.try_validate,
                'amount_untaxed': Pick.sale_id and '%s %s' % (Pick.sale_id.amount_untaxed, Pick.sale_id.currency_id.name) or False
                }
            for obj in ['box_id', 'user_id', 'partner_id', 'sale_id', 'purchase_id']:
                obj_id = Pick[obj]
                if obj_id:
                    vals[obj] = {'id': obj_id.id, 'name': obj_id.name}
                else:
                    vals[obj] = False
            
            if Pick.sale_ids:
                vals['sale_ids_str'] = ','.join(Pick.mapped('sale_ids.name')),
            if Pick.purchase_ids:
                vals['purchase_ids_str'] = ','.join(Pick.mapped('purchase_ids.name')),
            for obj in ['sale_ids', 'purchase_ids']:
                obj_ids = Pick[obj]
                vals_ids = []
                if obj_ids:
                    for obj_id in obj_ids:
                        vals_ids += [{'id': obj_id.id, 'name': obj_id.name}]
                    vals[obj] = vals_ids
                else:
                    vals[obj] = False
        # _logger.info(vals)
            
        return vals

    def check_allow_pda_validation(self):
        return True

    def action_transfer(self):
        res = super().action_transfer()
        self.write({'try_validate': False})
        return res

    def get_filters(self):
        filters = [
            {'name': 'Estado', 'field': 'state'},
            {'name': 'Transportista', 'field': 'carrier_id'},
        ]
        return super().get_filters(filters)

    ### LOTES DESDE EL LISTADO
    @api.model
    def get_lot_domain(self, values):
        batch_id = self.browse(self._context['id'])
        location_id = batch_id.mapped('move_lines.location_id')
        location_id.ensure_one()
        return batch_id.mapped('line_ids.product_id').get_lot_domain(location_id=location_id.id)

    def action_view_stock_move_lines(self):
        action = self.env.ref("stock.stock_move_line_action").read()[0]
        # action['view_mode'] = 'form'
        # del action['views']
        # del action['view_id']
        action["context"] = {}
        action["domain"] = [("id", "in", self.picking_ids.mapped("move_line_ids").ids)]
        return action

    def clear_empty_batchs(self):
        domain = []
        self.search(domain).filtered(lambda x: not x.picking_ids).unlink()

    @api.multi
    def compute_needed_space_in_box(self):
        for batch in self:
            needed_space = 0.00
            for sml in self.move_line_ids:
                needed_space += sml.product_id.volume_factor / 100 * sml.product_id.volume * sml.product_uom_qty
            batch.needed_space = needed_space

    def assign_box_id(self, only_free=False):
        volume = self.volume
        domain = [('is_box', '=', True), ('volume', '>=', volume)]
        if only_free:
            used_box_domain = [('box_id', '!=', False), ('state', '!=', 'done')]
            used_box_ids = self.env['stock.picking.batch'].search(used_box_domain).mapped('box_id')
            domain += [('id', 'not in', used_box_ids.ids)]
        box_id = self.env['stock.location'].search(domain, order='volume asc', limit=1)
        if not box_id:
            # Debería de ser customer ????
            box_id = self.picking_type_id.default_location_dest_id
        _logger.info("Buscando box para %s. Se envuentra %s, con volumen: %s" % (self.volume, box_id.display_name, box_id.volume))
        self.move_line_ids.write({'location_dest_id': box_id.id})
        self.box_id = box_id
        return box_id

    @api.multi
    def auto_assign_box_id(self):
        for batch in self.filtered(lambda x: not x.box_id and x.picking_type_id.code == 'outgoing'):
            box_id = batch.assign_box_id()
            _logger.info("Autoasignando box %s a %s" % (box_id.name, batch.name))

    @api.model
    def mark_as_pda_validate(self, vals):
        batch_id = vals.get('id', False)
        self.browse(batch_id).try_validate = True
        return True

    @api.model
    def button_validate_apk(self, vals):
        ctx = self._context.copy()
        ctx.update(skip_overprocessed_check=True)
        batch_id = self.with_context(ctx).browse(vals.get("id", False))
        if not batch_id:
            raise ValidationError("No se ha encontrado el albarán ")
        
        if batch_id.picking_type_id:
            g_code = batch_id.picking_type_id
            if g_code.need_weight and batch_id.carrier_weight == 0.00:
                raise ValidationError("Rellena el peso del albarán")
            if g_code.need_package and batch_id.carrier_packages == 0:
                raise ValidationError("Rellena el número de bultos")
        line_ids = batch_id.move_line_ids.filtered(lambda m: m.state not in ("done", "cancel"))
        qty_done = sum(move_line.qty_done for move_line in line_ids)
        if not qty_done:
            raise ValidationError("No hay ninguna cantidad para validar")
        if not batch_id.check_allow_pda_validation():
            raise ValidationError("No se ha superado los requerimientos para validar")
        _logger.info("Validando batch %s " % batch_id.name)

        for pick in batch_id.picking_ids:
            try:
                _logger.info("Validando albarán %s" % pick.name)
                pick.with_context(ctx).action_done()
            except Exception as err:
                msg = "Se ha intentado validar el albarán con el error:<br\> <strong>{}</strong>".format(
                    err
                )
                pick.note = '{}\n{}'.format(pick.note, msg)
                pick.message_post(body=msg)
                _logger.info("APK. {}".format(msg))
        _logger.info("Validación completa")
        # batch_id._cr.commit()
        # threaded_validation = threading.Thread(target=batch_id._thread_apk_validate_batch, args=())
        # threaded_validation.start()
        # _logger.info("Validción en otro hilo: OK")
        batch_id.try_validate = False
        return True

    def _thread_apk_validate_batch(self):
        with api.Environment.manage():
            # As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            new_cr = self.pool.cursor()
            ctx = self._context.copy()
            ctx.update(skip_overprocessed_check=True)
            self = self.with_context(ctx)
            self = self.with_env(self.env(cr=new_cr))
            _logger.info("Validando %s en un hilo nuevo" % self.name)
            for pick in self.picking_ids:
                try:
                    _logger.info("Validando albarán %s" % pick.name)
                    pick.with_context(ctx).action_done()
                except Exception as err:
                    msg = "Se ha intentado validar el albarán con el error:<br\> <strong>{}</strong>".format(
                        err
                    )
                    pick.note = '{}\n{}'.format(pick.note, msg)
                    pick.message_post(body=msg)
                    _logger.info("APK. {}".format(msg))
            self.try_validate = True
            new_cr.close()
            _logger.info("Validación completa")
            return True
