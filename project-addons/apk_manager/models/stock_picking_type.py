from odoo import api, fields, models, _
#from pprint import pprint
from .apk_manager import LIMIT

import logging
_logger = logging.getLogger(__name__)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    location_barcode = fields.Char('Reg. Ubicación', help="Expresión regular para leer ubiaciones")

class StockPickingType(models.Model):

    _inherit = "stock.picking.type"

    app_integrated = fields.Boolean("Show in app", default=False)
    allow_overprocess = fields.Boolean(
        "Overprocess", help="Permitir realizar más cantidad que la reservada"
    )
    icon = fields.Char("Icono")
    default_location = fields.Selection(
        selection=[("location_id", "Origen"), ("location_dest_id", "Destino")],
        string="Tipo de ubicación por defecto",
    )
    need_loc_before_qty = fields.Boolean('Confirma ubic antes de cant.?', help="Si está marcado, la aplicación necesitará confimar ubicaciones antes que cambiar las cantidades", default=False)
    need_location_dest_id = fields.Boolean('Confirma destino?', help="Si está marcado, la aplicación necesitará confimar destino para cada movimiento", default=False)
    need_location_id = fields.Boolean('Confirma origen?', help="Si está marcado, la aplicación necesitará confimar origen para cada movimiento", default=False)
    allow_change_location_id = fields.Boolean('Cambiar origen?', help="Si está marcado, la aplicación permite cambiar origen", default=False)
    allow_change_location_dest_id = fields.Boolean('Cambiar destino?', help="Si está marcado, la aplicación permite cambiar destino", default=False)
    need_confirm_lot_id = fields.Boolean('Confirma Lote?', help="Si está marcado, la aplicación necesitará confimar el lote", default=False)
    need_confirm_product_id = fields.Boolean('Confirma Artículo?', help="Si está marcado, la aplicación necesitará confimar el artículo antes de nada", default=False)
    next_move_on_qty_done = fields.Boolean('Auto Siguiente', help="Si está marcado, la aplicación saltará al siguiente movimiento una vez todos hechos", default=False)
    validate_on_finish = fields.Boolean('Auto Validación', help="Si está marcado, la aplicación validará automaticamente", defualt=False)
    count_picking_batch_ready = fields.Integer(compute="_compute_picking_batch_count")
    icon = fields.Char("Icono")
    location_barcode = fields.Char(related="warehouse_id.location_barcode")
    need_package = fields.Boolean("Paquetes", help="Si está marcado no permite validar con paquetes a 0")
    need_weight = fields.Boolean("Peso", help="Si está marcdo no permite validar con peso a 0.00")

    

    @api.model
    def TypeData(self, values):
        Res_Locs = {}
        domain = values.get('domain', [('app_integrated', '=', True)])
        product_ids = self.search(domain)
        _logger.info("Listado de %d artículos" %len(product_ids))
        return product_ids.get_apk_values()

    @api.model
    def get_apk_info(self, values):
        domain = [('app_integrated', '=', True), ('sequence_id.code', '=', 'stock.picking')]
        res_all = []
        for type in self.search(domain):
            res = {
                'id': type.id,
                'name': type.name,
                'location_id': type.default_location_src_id and {'id': type.default_location_src_id.id, 'name': type.default_location_src_id.name } or False,
                'count_picking_batch_ready': type.count_picking_batch_ready,
                'count_picking_waiting': 0,
                'count_picking_late': 0,
                'count_picking_ready': 0,
                'count_picking_backorders': 0,
                'code': type.sequence_id.code
            }
            res_all.append(res)
        return res_all

    def get_apk_fields(self):
        type_id = self
        return {
                'id': type_id.id,
                'name': type_id.barcode,
                'warehouse_id': {'id': type_id.warehouse_id.id, 'name': type_id.warehouse_id.name},
                'allow_overprocess': type_id.allow_overprocess,
                'bypass_tracking': type_id.bypass_tracking,
                'use_existing_lots': type_id.use_existing_lots,
                'use_create_lots': type_id.use_create_lots,
                'default_location': type_id.default_location,
                'location_barcode': type_id.location_barcode,
                'need_loc_before_qty': type_id.need_loc_before_qty,
                'need_location_dest_id': type_id.need_location_dest_id,
                'need_confirm_lot_id': type_id.need_confirm_lot_id,
                'need_confirm_product_id': type_id.need_confirm_product_id,
                'need_location_id': type_id.need_location_id,
                'allow_change_location_dest_id': type_id.allow_change_location_dest_id,
                'allow_change_location_id': type_id.allow_change_location_id,
                'next_move_on_qty_done': type_id.next_move_on_qty_done,
                'validate_on_finish': type_id.validate_on_finish,
                'need_weight': type_id.need_weight,
                'need_package': type_id.need_package,
            }

    @api.multi
    def get_apk_values(self, values={}):
        if values:
            id = values.get('picking_type_id', False)
        if not self:
            type_id = self.browse(id)
        res = []
        for type_id in self:
            values = type_id.get_apk_fields()
            res.append(values)
        return res

    @api.model
    def get_apk_tree(self, values):
        picking_type_id = values.get('picking_type_id', False)
        state = values.get('state', False)
        model = values.get('model', 'stock.picking.batch')
        limit = values.get('limit', LIMIT)
        offset = values.get('offset', 1)
        domain = values.get('domain', False)
        if domain:
            domain = domain
        else:
            domain = []
        if picking_type_id:
            domain += [('picking_type_id', '=', picking_type_id)]
        if state:
            domain += [('state', '=', state)]

        Picks = self.env[model].with_context(prefetch_fields=False).search(domain, limit=limit, offset=offset)
        res = []
        for Pick in Picks:
            pick = Pick.get_apk_tree_values()
            res.append(pick)
        Filters = Picks.get_filters()
        vals = {'Picks': res, 'Filter': Filters}
        return vals
        ## Inicialmente voy a hacer por albaranes, aunque las funciones deberían de ser siempre las mismas

    def get_action_picking_batch_tree_ready(self):
        action = self._get_action(
            "stock_picking_batch_extended.action_stock_batch_picking_tree"
        )
        action["domain"] = self.get_picking_batch_domains()[
            "count_picking_batch_ready"
        ] + [("picking_type_id", "in", self.ids)]
        return action

    def get_picking_batch_domains(self):
        return {
            "count_picking_batch_ready": [("state", "in", ["assigned", "in_progress"])]
        }

    @api.multi
    def _compute_picking_batch_count(self):
        domains = self.get_picking_batch_domains()
        for field in domains:
            data = self.env["stock.picking.batch"].read_group(
                domains[field] + [("picking_type_id", "in", self.ids)],
                ["picking_type_id"],
                ["picking_type_id"],
            )
            count = {
                x["picking_type_id"][0]: x["picking_type_id_count"]
                for x in data
                if x["picking_type_id"]
            }
            for record in self:
                record[field] = count.get(record.id, 0)
