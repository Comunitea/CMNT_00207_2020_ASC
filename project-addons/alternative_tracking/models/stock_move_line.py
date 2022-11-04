# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from time import time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
# from odoo.tools.float_utils import float_compare
from odoo.addons.alternative_tracking.models.product_product import TRACKING_VALUES

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.multi
    def _get_available_serial_ids(self):
        # Devuelve los números dee serie disponibles para este move_line
        spl = self.env["stock.production.lot"]
        for line in self.filtered(lambda x: x.template_tracking == 'virtual'):
            move_orig_ids = (line.move_id.origin_returned_move_id | line.move_id.move_orig_ids)
            location_id = line.location_id
            product_id = line.product_id
            # Si tiene moveimientos previosm entonces los series solo pueden ser de aquí y con ubicación en el mismo sitio
            if move_orig_ids:
                domain = [
                    ("location_id", "child_of", location_id.serial_location.id),
                    ("id", "in", move_orig_ids.mapped("serial_ids").ids),
                ]
            else:
                domain = product_id.get_serial_domain(location_id=location_id.serial_location)
            line.available_serial_ids = spl.search(domain)

    serial_ids = fields.Many2many(
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
        comodel_name='virtual.serial',
        inverse_name="move_line_id",
        string="Future lots",
        help="Future lot ids, convert to lot when sml is done. Borrados en el action done")
    lot_ids_string = fields.Text("Serial list to add", help="Technical field to conver texto to serial_name_ids. Conver to serial_name_ids")
    # virtual_tracking = fields.Boolean(related='product_id.virtual_tracking', store=True)
    # TODO compute store
    template_tracking = fields.Selection(related='product_id.product_tmpl_id.template_tracking') #, store=True)
    # tracking = fields.Selection(selection=TRACKING_VALUES, default='none')
    picking_type_id = fields.Many2one(related="move_id.picking_type_id")
    serial_location = fields.Many2one(related="location_id.serial_location")
    show_name_ids = fields.Boolean(string="Use barcode reader", default=False)

    @api.multi
    def apply_lot_ids_string(self):
        self.ensure_one()
        lot_ids_string = self._context.get("lot_ids_string", False) or self.lot_ids_string
        if lot_ids_string:
            self.create_move_serial_from_list(lot_ids_string)
            self.lot_ids_string = ''

    def compute_names_from_string(self, lot_names):
        if not lot_names:
            return []
        # Si lot_names es una cadena: Reemplazo los . y las , por retorno de carro y separo por lineas para hacer una lista
        if type(lot_names) is str:
            lot_names = lot_names.replace(".", "\n").replace(",", "\n").replace("\n", " ").split(" ")
        # Si no es una lista fallo
        if not (type(lot_names) is list):
            raise ValidationError(_("Values in unknown format"))
        # Elimino los vacíos, nulos, y repetidos de la lista
        res = []
        not_lot_name = []
        if self.product_id.not_lot_name_ids:
            not_lot_name = self.product_id.not_lot_name_ids.mapped('name')
        for lot in lot_names:
            if lot and lot not in res and lot not in not_lot_name:
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

    def create_move_serial_from_list(self, lot_names):
        # Si lot_names es una cadena: Reemplazo los . y las , por retorno de carro y separo por lineas para hacer una lista
        lot_names = self.compute_names_from_string(lot_names)
        # Tengo que crear los virtual.serial
        serial_names = self.serial_name_ids.mapped('name')
        for lot_name in sorted(lot_names):
            if lot_name not in serial_names:
                self.env['virtual.serial'].create({'name': lot_name, 'move_line_id': self.id})
                serial_names.append(lot_name)
        return True

    @api.onchange('serial_ids', 'serial_name_ids')
    def onchange_lot_ids(self):
        if self.state in ["done", "cancel", "draft"]:
            raise ValidationError(_("Incorrect move state"))
        if self.template_tracking == 'virtual' and not self._context.get("by_pass_compute_qties", False):
            self.qty_done = len(self.serial_ids) + len(self.serial_name_ids) 

    @api.multi
    def action_alternative_tracking_in_move_line(self):
        self.ensure_one()
        # if self.get_use_create_lots():
        #  view = self.env.ref("alternative_tracking.stock_move_line_tracking_form_tree_serial")
        # else:
        view = self.env.ref("alternative_tracking.stock_move_line_tracking_form_tree_serial")
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
        ##            field = self.env['stock.move'].browse(val['move_id']).picking_type_id.default_location
        ##            val.update(removal_priority = self.env['stock.location'].browse(val.get(field)).removal_priority)
        return super().create(vals)

    @api.onchange('location_id', 'location_dest_id')
    def onchange_location_priority(self):
        """
        if isinstance(self.move_id.id, int):
            field = self.move_id.picking_type_id.default_location
            self.removal_priority = self[field].removal_priority
        else:
            picking_type_id = self._context.get('default_picking_type_id', False)
            if picking_type_id:
                field = self.env['stock.picking.type'].browse(picking_type_id).default_location
                self.removal_priority = self[field].removal_priority
        """
        return

    @api.multi
    def write(self, vals):
        if vals.get('lot_ids_string', False):
            lot_names = self.env['stock.move.line'].compute_names_from_string(vals['lot_ids_string'])
            vals['lot_ids_string'] = ",".join(lot_names)
        res = super().write(vals)
        if 'serial_name_ids' in vals and 'qty_done' not in vals:
            #self._context.get('recal_qty_done', False): 
            for sml_id in self:
                sml_id.qty_done = len(self.serial_name_ids)
        return res

    def write_new_virtual_location(self):
        for sml_id in self:
            location_id = sml_id.location_dest_id.serial_location or sml_id.location_dest_id
            sml_id.serial_ids.write({
                'real_location_id': sml_id.location_dest_id.id,
                'location_id': location_id.id
            })

    def _action_done(self):
        if not self or not self[0].product_id.virtual_tracking:
            return super()._action_done()
        type_id = self.mapped('picking_type_id')
        if not type_id or len(type_id) > 1:
            # _logger.info ("El movimiento {} : {} no tiene tipo (o no es único)".format(self.mapped('display_name'), self.ids))
            return super()._action_done()
        if type_id.bypass_tracking:
            super()._action_done()
            # Hago un action done, pero escribo las nuevas ubicaiones para los serial si los hay
            for sml_id in self:
                if sml_id.serial_ids:
                    sml_id.write_new_virtual_location()
            return
        move_ids = self.mapped('move_id').filter_affected_moves()
        # TODO qty_done > 0 ????
        virtual_tracking_move_ids = self.filtered(lambda x: x.qty_done > 0 and x.state != 'done' and x.move_id in move_ids)
        res = super()._action_done()
        if not virtual_tracking_move_ids:
            return super()._action_done()
        use_create_lots = virtual_tracking_move_ids[0].get_use_create_lots()
        for sml_id in virtual_tracking_move_ids:
            if (not sml_id.serial_ids and not sml_id.serial_name_ids) and sml_id.qty_done > 0:
                raise ValidationError(_("You need serial numbers"))
            create_vals = []
            to_create = sml_id.serial_name_ids.filtered(lambda x: not x.lot_id)
            serial_ids = sml_id.serial_name_ids - to_create
            ## todos los serial_name_ids deberían de tener un spl
            for serial_id in sml_id.serial_name_ids.filtered(lambda x: not x.lot_id):
                if not use_create_lots:
                    raise ValidationError(_("Type not permit serial creation"))
                lot_vals = {
                    "product_id": sml_id.product_id.id,
                    "location_id": sml_id.location_id.serial_location.id,
                    "real_location_id": sml_id.location_id.id,
                    "name": serial_id.name,
                    }
                create_vals.append(lot_vals)
            if create_vals:
                sml_id.write({'serial_ids': [(0, 0, val) for val in create_vals]})
            if serial_ids:
                sml_id.write({'serial_ids': [(4, val) for val in serial_ids.mapped('lot_id').ids]})
                serial_location = sml_id.picking_id.location_id.serial_location
                location_ids = sml_id.serial_ids.mapped('location_id')
                if any(x != serial_location for x in location_ids):
                    error_serial = []
                    for lot_id in sml_id.serial_ids:
                        if lot_id.location_id != serial_location:
                            error_serial += [lot_id.name]
                    if error_serial:
                        msgbox = 'Los lotes {} no están en la ubicación correcta'.format(','.join(x for x in error_serial))
                        if not sml_id.picking_type_id.bypass_serial_error_location:
                            raise ValidationError(msgbox)
                        sml_id.picking_id.message_post(body=msgbox)
            if sml_id.picking_type_id.check_serial_qties:
                if len(sml_id.serial_ids) != sml_id.qty_done:
                    raise ValidationError(_('Los números de serie no coinciden con la cantidad hecha'))
            sml_id.write_new_virtual_location()
            sml_id.show_name_ids = True
            ## Podría borrarlos pero de momento los dejo
        return res
