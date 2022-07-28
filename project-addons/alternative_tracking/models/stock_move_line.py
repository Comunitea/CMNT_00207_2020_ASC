# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
# from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
    
    @api.multi
    def _get_available_serial_ids(self):
        ## Devuelve los números dee serie disponibles para este move_line
        spl = self.env["stock.production.lot"]
        for line in self.filtered(lambda x: x.product_id.virtual_tracking):
            move_orig_ids = (line.move_id.origin_returned_move_id | line.move_id.move_orig_ids)
            location_id = line.location_id
            product_id = line.product_id
            ## Si tiene moveimientos previosm entonces los series solo pueden ser de aquí y con ubicación en el mismo sitio
            if move_orig_ids:
                domain = [
                    ("location_id", "child_of", location_id.serial_location.id),
                    ("id", "in", move_orig_ids.mapped("lot_ids").ids),
                ]
            else:
                domain = product_id.get_lot_domain(location_id=location_id.serial_location)
            line.available_serial_ids = self.env["stock.production.lot"].search(domain)


    lot_ids = fields.Many2many(
            comodel_name="stock.production.lot",
            relation="lot_id_move_line_id_rel",
            column1="move_line_id",
            column2="lot_id",
            string="Lots",
            copy=False,
        )
    available_serial_ids = fields.One2many(
        "stock.production.lot", compute=_get_available_serial_ids
    )
    serial_name_ids = fields.One2many(
        comodel_name = 'virtual.serial',
        inverse_name="move_line_id",
        string="Future lots",
        help="Future lot ids, convert to lot when sml is done. Borrados en el action done")

    lot_ids_string = fields.Text("Serial list to add", help="Technical field to conver texto to serial_name_ids. Conver to serial_name_ids")
    virtual_tracking = fields.Boolean(related='product_id.virtual_tracking', store=True)
    tracking = fields.Selection(related='product_id.template_tracking', store=True)
    
    @api.multi
    def apply_lot_ids_string(self):
        self.ensure_one()
        lot_ids_string = self._context.get("lot_ids_string", False) or self.lot_ids_string
        if lot_ids_string:
            self.create_move_lots_from_list(lot_ids_string)
            self.lot_ids_string = ''
            

    def compute_names_from_string(self, lot_names):
        if not lot_names:
            return []
        # Si lot_names es una cadena: Reemplazo los . y las , por retorno de carro y separo por lineas para hacer una lista
        if type(lot_names) is str:
            lot_names = lot_names.replace(".", "\n").replace(",", "\n").replace("\n", " ").split(" ")
        ## Si no es una lista fallo
        if not (type(lot_names) is list):
            raise ValidationError(_("Values in unknown format"))
        ## Elimino los vacíos, nulos, y repetidos de la lista
        res = []
        for lot in lot_names:
            if lot and lot not in res:
                res.append(lot)
                
            
        return sorted(res)

    def get_use_create_lots(self):
        move_id = self.move_id
        picking_type_id = move_id.picking_type_id
        if picking_type_id:
            use_create_lots = picking_type_id and picking_type_id.use_create_lots 
        elif move_id.inventory_id:
            use_create_lots = True
        else:
            use_create_lots = False
        return use_create_lots


    def create_move_lots_from_list(self, lot_names, virtual_tracking=True, compute_qties=True, assign_sml=False, add_lots=True):
        # Si lot_names es una cadena: Reemplazo los . y las , por retorno de carro y separo por lineas para hacer una lista
        move_id = self.move_id
        lot_names = self.compute_names_from_string(lot_names)
        product_id = move_id.product_id
        values = []
        ## Tengo que crear los virtual.serial
        serial_names = self.serial_name_ids.mapped('name')
        for lot_name in sorted(lot_names):
            if lot_name not in serial_names:
                self.env['virtual.serial'].create({'name': lot_name, 'move_line_id': self.id})
                serial_names.append(lot_name)
        return

    @api.onchange('lot_ids', 'serial_name_ids')
    def onchange_lot_ids(self):
        if self.state in ["done", "cancel", "draft"]:
            raise ValidationError(_("Incorrect move state"))
        if self.virtual_tracking and not self._context.get("by_pass_compute_qties", False):
            self.qty_done = len(self.lot_ids) + len(self.serial_name_ids) 

    @api.multi
    def action_alternative_product(self):
        self.ensure_one()
        view = self.env.ref("alternative_tracking.stock_move_line_tracking_form")
        return {
            "name": _("Tracking Form Operations"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "stock.move.line",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "res_id": self.id,
        }

    @api.multi
    def action_open_tracking_form(self):
        self.ensure_one()
        view = self.env.ref("alternative_tracking.stock_move_line_tracking_form")
        return {
            "name": _("Tracking Form Operations"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "stock.move.line",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "res_id": self.id,
        }

    def create(self, vals):
        ## ESTO REALMENTE VA AQUÍ
        ## if isinstance(vals, list):
        ##    for val in vals:
        ##        if not 'removal_priority' in val and val.get('move_id', False):
        ##            field = self.env['stock.move'].browse(val['move_id']).picking_type_id.group_code.default_location
        ##            val.update(removal_priority = self.env['stock.location'].browse(val.get(field)).removal_priority)
        return super().create(vals)

    @api.onchange('location_id', 'location_dest_id')
    def onchange_location_priority(self):
        return
        ## ESTO REALMENTE VA AQUÍ
        if isinstance(self.move_id.id, int):
            field = self.move_id.picking_type_id.group_code.default_location
            self.removal_priority = self[field].removal_priority
        else:
            picking_type_id = self._context.get('default_picking_type_id', False)
            if picking_type_id:
                field = self.env['stock.picking.type'].browse(picking_type_id).group_code.default_location
                self.removal_priority = self[field].removal_priority

    @api.multi
    def write(self, vals):
        if vals.get('lot_ids_string', False):
            lot_names = self.env['stock.move.line'].compute_names_from_string(vals['lot_ids_string'])
            vals['lot_ids_string'] = ",".join(lot_names)
        res = super().write(vals)
        if 'serial_name_ids' in vals and not 'qty_done' in vals: #self._context.get('recal_qty_done', False): 
            for sml_id in self:
                sml_id.qty_done = len(self.serial_name_ids)
        return res     
    
    def write_new_virtual_location(self):
        for sml_id in self:
            location_id = sml_id.location_dest_id.serial_location or sml_id.location_dest_id
            sml_id.lot_ids.write({
                'real_location_id': sml_id.location_dest_id.id,
                'location_id': location_id.id
            })

    def _action_done(self):

        type_id = self.mapped('picking_type_id')
        
        if not type_id or len(type_id) > 1:
            _logger.info ("El movimiento {} : {} no tiene tipo (o no es único)".format(self.mapped('display_name'), self.ids))
            return super()._action_done()
        
        if type_id.bypass_tracking:
            return super()._action_done()

        move_ids = self.mapped('move_id').filter_affected_moves()
        ## TODO qty_done > 0 ????
        virtual_tracking = self.filtered(lambda x: x.qty_done > 0 and x.state != 'done' and x.move_id in move_ids)
        res = super()._action_done()
        if not virtual_tracking:
            return res
        
        use_create_lots = self.get_use_create_lots()
        for sml_id in virtual_tracking:
            if not sml_id.serial_name_ids and sml_id.qty_done > 0:
                raise ValidationError(_("You need serial numbers"))
                
            serial_names = sml_id.serial_name_ids.mapped('name')
            sql = "select id, name from stock_production_lot where name in (%s) and product_id = %d" %(','.join(x.name for x in serial_names), sml_id.product_id.id)
            self._cr.execute(sql)
            res = self._cr.fetchall()
            lot_names = [x['name'] for x in res]
            lot_ids = [x['id'] for x in res]
            existing = to_create = []
            for lot_name in sorted(serial_names):
                if lot_name in lot_names:
                    existing.append(lot_name)
                else:
                    to_create.append(lot_name)
            
            if to_create and not use_create_lots:
                raise ValidationError(_("Type not permit serial creation"))
            ## Creo los lotes que hagan falta en la ubicación
            create_vals = []
            for lot_name in sorted(serial_names):
                ## Tengo que crear un lote por cada lot name
                lot_vals = {
                            "product_id": sml_id.product_id.id,
                            "location_id": sml_id.location_id.serial_location.id,
                            "real_location_id": sml_id.location_id.id,
                            "name": lot_name,
                            "ref": lot_name,
                            "virtual_tracking": True}
                create_vals.append(lot_vals)
            
            if create_vals:
                sml_id.write({'lot_ids': [(0, 0, val) for val in create_vals]})
            if lot_ids:
                sml_id.write({'lot_ids': [(6, 0, lot_ids)]})
  
    
        virtual_tracking.write_new_virtual_location()
        ## Podría borrarlos pero de momento los dejo
        ## virtual_tracking.mapped('serial_name_ids').unlink()
        
        return res
