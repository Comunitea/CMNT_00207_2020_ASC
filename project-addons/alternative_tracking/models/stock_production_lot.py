# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# from odoo.tools.float_utils import float_compare
import logging

from odoo import _, api, fields, models
# from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

LOT_NAMES_TYPES = [
    ("supplier", "Vendor Location"),
    ("view", "View"),
    ("internal", "Internal Location"),
    ("customer", "Customer Location"),
    ("inventory", "Inventory Loss"),
    ("procurement", "Procurement"),
    ("production", "Production"),
    ("transit", "Transit Location"),
]


from odoo import tools
from odoo import api, fields, models

class VirtualProductionLot(models.Model):
    _name = 'virtual.serial'

    name = fields.Char('name')
    move_line_id = fields.Many2one('stock.move.line', string="Related Move Line")

    @api.multi
    def convert_to_spl(self, move_line_id, product_id, location_id):
        ## Convierte una lista de virtual serial a lotes de odoo
        ## Y lo añade a un stock_move_line 
        domain = [
            ('product_id', '=', product_id.id), 
            ('name', 'in', self.mapped('name')), 
            '|', ('active', '=', True), ('active', '=', False)]
        lot_ids = self.env['stock.production.lot'].search(domain)

        id_to_link = []
        values_to_link = []
        for vpl_id in self:
            spl_id = lot_ids.filtered(lambda x: x.name == vpl_id.name)
            if spl_id:
                ## Ya existe, por lo que lo añado.
                if not spl_id.active:
                    spl_id.active = True
                id_to_link += [spl_id]
            else:
                ## Los tengo que crear.
                values = {
                    'name': vpl_id.name,
                    'product_id': product_id.id,
                    'location_id': location_id.serial_location.id,
                    'real_location_id': location_id.id,
                    'ref': vpl_id.name}
                values_to_link += [values]
        if id_to_link:
            move_line_id.lot_ids = [(4, id) for id in id_to_link]
        if values_to_link:
            move_line_id.lot_ids = [(0, 0, values) for values in values_to_link]

class VirtualLastLoc(models.Model):
    _name = "virtual.last.location"
    _description = "Virtual Serial Last Location"
    _auto = False
    _rec_name = 'lot_id'
    _order = 'date desc'

    @api.model
    def _get_done_states(self):
        return ['sale', 'done', 'paid']

    location_id = fields.Many2one(comodel_name='stock.location', string="Actual Location", readonly=True)
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string="Virtual Serial", readonly=True)
    product_id = fields.Many2one(comodel_name='product.product', string="Producto", readonly=True)
    date = fields.Datetime('Order Date', readonly=True)

    def _query(self):
        select_ = """
            select
            sml.id as id,
            lmlrel.lot_id as lot_id,
            sml.product_id as product_id,
            sml.date as date,
            sml.location_dest_id as location_id
            from stock_move_line sml
            join lot_id_move_line_id_rel lmlrel on lmlrel.move_line_id = sml.id
            where sml.state = 'done'
        """
        return select_

    @api.model_cr
    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    virtual_tracking = fields.Boolean(related='product_id.virtual_tracking', store=True)
    location_id = fields.Many2one("stock.location", "Virtual Location")
    real_location_id = fields.Many2one("stock.location", "Real Location")
    location_id_usage = fields.Selection(related="location_id.usage")
    move_line_ids = fields.One2many(
        "stock.move.line", compute="_compute_tracking_moves"
    )

    @api.multi
    def unlink(self):
        sql = "select move_line_id from lot_id_move_line_id_rel where lot_id in %s"
        self._cr.execute(sql, [tuple(self.ids)])
        res = self._cr.fetchall()
        if res:
            raise ValidationError (_('Hay lotes que ya han sido utilizados en algún movimiento'))
        return super().unlink()

    @api.multi
    def _compute_tracking_moves(self):
        for lot in self:
            domain = [("state", "=", "done"), '|', ('lot_id', '=', lot.id), ("lot_ids", "=", lot.id)]
            lot.move_line_ids = self.env["stock.move.line"].search(domain, order="date asc")

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        ##Añado el filtro available para ver si hay stock para esos lotes ????
        if self._context.get("available", False):
            stock_location = self._context.get('stock_location')
            if not stock_location:
                stock_location = self.env.ref('stock.stock_location_stock')
            d1 = self.env['product.product'].get_lot_domain(location_id = stock_location.id)
            args = expression.normalize_domain(args)
            args = expression.AND([d1, args])
        res = super().search(args, offset=offset, limit=limit, order=order, count=count)
        return res
     

    @api.model
    def create(self, vals):
        if not vals.get('real_location_id') and vals.get('location_id'):
            vals['real_location_id'] = vals['location_id']
        if not vals.get('location_id') and vals.get('real_location_id'):
            serial_location = self.env['stock.location'].browse(vals['real_location_id']).serial_location
            vals['location_id'] = serial_location.id
        return super().create(vals)

    def update_real_location_id(self):
        if not self:
            self = self.search([])
        for lot in self.filtered(lambda x: x.virtual_tracking):
            _logger.info("Actualizando {}".format(lot.name))
            domain = [('lot_id', '=', lot.id)]
            vll_id = self.env['virtual.last.location'].search(domain, limit=1)
            if vll_id:
                lot.location_id = vll_id.location_id.serial_location
                lot.real_location_id = vll_id.location_id
            else:
                if not lot.real_location_id and lot.location_id:
                    lot.real_location_id = lot.location_id
            _logger.info(">>>> De {} ({}) a {}".format(lot.location_id.display_name, lot.real_location_id.display_name, real_location_id.display_name))
