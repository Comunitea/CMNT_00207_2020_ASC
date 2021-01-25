
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def set_new_location_path(self, location_id):
        newpath = location_id
        putaway_strategy_id = self.env['product.putaway']
        
        while location_id and not putaway_strategy_id:
            putaway_strategy_id =  location_id.putaway_strategy_id
            location_id = location_id.location_id
        if not putaway_strategy_id:
            raise ValidationError (_('Not putaway strategy for %s'% newpath.name))

        domain = [('product_id', 'in', self.ids), ('putaway_id', '=', putaway_strategy_id.id)]
        putaway_ids = self.env['stock.fixed.putaway.strat'].search(domain)
        for put in putaway_ids:
            put.sequence += 1
        for product_id in self:
            vals = {'sequence': 0, 
                    'product_id': product_id.id, 
                    'fixed_location_id': newpath.id,
                    'putaway_id':putaway_strategy_id.id }
            self.env['stock.fixed.putaway.strat'].create(vals)


class StockMoveLocationWizard(models.TransientModel):
    _inherit = "wiz.stock.move.location"

    product_ids = fields.Many2many('product.product', string='Products')
    apply_to_location_path = fields.Boolean('Ubicación por defecto', default=True)
    picking_ids = fields.Many2many('stock.picking')
    all_done = fields.Boolean('En un paso')

    def _get_picking_action(self, pickinig_id):
        ids = self.picking_ids.ids + [pickinig_id]
        if self.all_done:
            picking_id = self.env['stock.picking'].browse(pickinig_id)
            for sml_id in picking_id.move_line_ids:
                sml_id.qty_done = sml_id.product_uom_qty
            picking_id.action_done()
            self.picking_ids.action_assign()
        if not self.picking_ids:
            return super()._get_picking_action(pickinig_id=pickinig_id)
        action = self.env.ref("stock.action_picking_tree_all").read()[0]
        form_view = self.env.ref("stock.view_picking_form").id
        action.update({
            'domain': [('id', 'in', ids)]
        })        
        return action


    @api.multi
    def action_move_location(self):
        product_ids = self.product_ids | self.stock_move_location_line_ids.mapped('product_id')
        if self.apply_to_location_path:
            product_ids.set_new_location_path(self.destination_location_id)
        ## debo de anular todos los movimientos sml del producto y ubicación de origen
        domain = [('location_id', 'child_of', self.origin_location_id.id), ('product_id', 'in', product_ids.ids), ('state', 'in', ('assigned', 'partially_available'))]
        sml_ids = self.env['stock.move.line'].search(domain)
        self.picking_ids = sml_ids.mapped('picking_id').filtered(lambda x: x.state == 'assigned')
        print ("Se han encontrado estos albaranes para reservar: %s"% self.picking_ids.mapped('name'))
        sml_ids.unlink()
        return super().action_move_location()
    

    def _get_group_quants(self):
        if not self.product_ids:
            return super()._get_group_quants()

        location_id = self.origin_location_id.id
        company = self.env['res.company']._company_default_get(
            'stock.inventory',
        )
        if self.product_ids:
            product_ids = tuple(self.product_ids.ids,)
        # Using sql as search_group doesn't support aggregation functions
        # leading to overhead in queries to DB

        query = """
            SELECT product_id, lot_id, SUM(quantity)
            FROM stock_quant
            WHERE location_id = %s and product_id in %s
            AND company_id = %s
            GROUP BY product_id, lot_id
        """
        self.env.cr.execute(query, (location_id, product_ids, company.id))
        return self.env.cr.dictfetchall()
