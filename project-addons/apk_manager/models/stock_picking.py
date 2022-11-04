from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
#from pprint import pprint
from .apk_manager import LIMIT
import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):

    _inherit = ["apk.model", "stock.picking"]
    _name = "stock.picking"

    @api.multi
    def _is_delayed(self):
        picking_ids = self.filtered(lambda x: x.state != 'done' and x.scheduled_date < fields.datetime.today())
        picking_ids.write({'delayed': True})

    delayed = fields.Boolean('Delayed', compute= _is_delayed)
    box_id = fields.Many2one(
        "stock.location", string="Box", domain=[("is_box", "=", True)]
    )
    try_validate = fields.Boolean("Validación desde PDA", default=False)

    def get_apk_tree_values(self):
        self.ensure_one() ## ?????
        for Pick in self:
            order_id = Pick.sale_id or Pick.purchase_id or False
            vals = {
                'id': Pick.id,
                'name': Pick.apk_name or Pick.name,
                'partner_id': Pick.partner_id and {'id': Pick.partner_id.id, 'name': Pick.partner_id.name} or False,
                'order_id': order_id and {'id': order_id.id, 'name': order_id.name} or False,
                'stock_move_count': len(Pick.move_lines),
                'product_count': sum(x.product_uom_qty for x in Pick.move_line_ids),
                'state': Pick.get_selection_dict_values('state', Pick.state),
                'box_id': Pick.box_id and {'id': Pick.box_id.id, 'name': Pick.box_id.name, 'barcode': Pick.box_id.barcode} or False,
                'batch_id': Pick.batch_id and {'id': Pick.batch_id.id, 'name': Pick.batch_id.name} or False,
                'info_str': Pick.info_str,
                'carrier_id': Pick.carrier_id and {'id': Pick.carrier_id.id, 'name': Pick.carrier_id.code} or False,
                'priority': Pick.get_selection_dict_values('state', Pick.priority),
                'quantity_done': Pick.quantity_done
                }
        return vals

    def get_filters(self):
        filters = [
            {'name':'Estado', 'field': 'state'},
            {'name':'Prioridad', 'field': 'priority'},
            {'name':'Transportista', 'field': 'carrier_id'},

        ]
        return super().get_filters(filters)

    @api.multi
    def assign_removal_priority(self):
        for pick in self:
            pick.move_line_ids.assign_removal_priority
            field = pick.picking_type_id.default_location or 'location_id'
            if field == "location_id":
                field_dest = "location_dest_id"
            else:
                field_dest = "location_id"
            pick.move_line_ids.assign_removal_priority(pick.box_id, field, field_dest)

    @api.model
    def action_assign_apk(self, vals):
        picking = self.browse(vals.get("id", False))
        if not picking:
            raise ValidationError(u"No se ha encontrado el albarán")
        picking.action_assign()
        return True

    @api.model
    def do_unreserve_apk(self, vals):
        picking = self.browse(vals.get("id", False))
        if not picking:
            raise ValidationError(u"No se ha encontrado el albarán")
        picking.do_unreserve()
        return True

    @api.model
    def cancel_batch(self, vals):
        picking_id = self.browse(vals.get("id", False))
        if not picking_id:
            return False
        if picking_id.quantity_done > 0:
            raise ValidationError ('El albarán %s tiene cantidades hechas'%picking_id.named)

        picking_id.batch_id = False
        picking_id.box_id = False


    @api.multi
    def auto_assign_batch_id(self):
        batch_ids = super().auto_assign_batch_id()
        batch_ids.auto_assign_box_id()
        return batch_ids