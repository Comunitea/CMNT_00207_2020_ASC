# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models, fields, _

class FixedPutAwayStrategy(models.Model):
    _inherit = 'stock.fixed.putaway.strat'

    from_script = fields.Boolean('From script auto')

    @api.multi
    def name_get(self):
        res = []
        print (self._context)
        for name in self:
            display_name = '{}: {}'.format(name.putaway_id.name, name.fixed_location_id.name)
            if self._context.get('with_product'):
                display_name = '{}: {}'.format(name.product_id.display_name, display_name)
            res.append((name.id, '%s' % (display_name)))
        return res


class ProductTemplate(models.Model):

    _inherit ='product.template'

    product_putaway_ids = fields.One2many(
        'stock.fixed.putaway.strat', string="Ubicaciones de traslado", compute="_compute_putaway_ids_ids", inverse="_set_putaway_ids",
        help="Gives the different ways to package the same product.")

    @api.depends('product_variant_ids', 'product_variant_ids.product_putaway_ids')
    def _compute_putaway_ids_ids(self):
        for p in self:
            if len(p.product_variant_ids) == 1:
                p.product_putaway_ids = p.product_variant_ids.product_putaway_ids

    def _set_putaway_ids(self):
        for p in self:
            if len(p.product_variant_ids) == 1:
                p.product_variant_ids.product_putaway_ids = p.product_putaway_ids


class ProductProduct(models.Model):

    _inherit ='product.product'

    product_putaway_ids = fields.One2many('stock.fixed.putaway.strat', 'product_id', 'Ubicaciones de traslado')

    @api.multi
    def open_product_putaway_strat(self):
        self.ensure_one()
        domain = [('id', 'in', self.product_putaway_ids.ids)]
        warehouse_id = self._context.get('warehouse_id', False)
        if not warehouse_id:
            warehouse_id = self.env['stock.warehouse'].search([], limit=1)

        location_id = warehouse_id.lot_stock_id

        action = self.env.ref('product_putaway.action_stock_fixed_putaway_strat_tree_pp').read()[0]

        action['view_mode'] = 'tree'

        action['domain'] = domain
        action['context'] = {'default_product_id': self.id,
                             'default_fixed_location_id': location_id.id,
                             'default_putaway_id': location_id.putaway_strategy_id.id,
                             'hide_product': True}
        return action

    def create_putaway_from_stock(self, location_id = False):
        if not location_id:
            location_id = self.env.user_id.company_id.warehouse_id.lot_stock_id

        strategic_id = location_id.putaway_strategy_id
        if not strategic_id:
            raise ValueError('La ubicación {} not tiene estrategia de traslado'.format(location_id.name))

        for product_id in self.filtered(lambda x: not x.product_putaway_ids):
            q_d = [
                ("product_id", "=", product_id.id),
                ("location_id", "child_of", [location_id.id]),
            ]
            sq = self.env["stock.quant"].search(
                q_d, order="quantity desc", limit=1
            )
            if sq:
                sfps = self.env['stock.fixed.putaway.strat']
                val = {'sequence': 1,
                       'putaway_id': strategic_id.id,
                       'product_id': product_id.id,
                       'fixed_location_id': location_id}

                sfps.create(val)

    @api.multi
    def _compute_putaway_from_stock(self, warehouse_id = False):

        if not warehouse_id:
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)
        if len(warehouse_id)!=1:
            raise ("Error de almacén")
        location_id = warehouse_id.lot_stock_id
        putaway_id = location_id.putaway_strategy_id

        Quant = self.env['stock.quant']
        putaway_ids = self.env['stock.fixed.putaway.strat']
        print ('Calculando nuevas ubicaciones para {}'.format(len(self)))
        for product_id in self:
            quant = Quant._gather(product_id, location_id)
            if quant:
                location_putaway_id = quant[0].location_id
                if location_putaway_id.usage == 'internal':
                    vals = {'sequence': 0, 'product_id': product_id.id, 'putaway_id': putaway_id.id, 'from_script': True,
                            'fixed_location_id': location_putaway_id.id}
                    domain = [('product_id', '=', product_id.id), ('putaway_id', '=', putaway_id.id), ('fixed_location_id', '!=', location_putaway_id.id)]
                    for line in self.env['stock.fixed.putaway.strat'].search(domain):
                        line.sequence += 1
                    domain = [('product_id', '=', product_id.id), ('putaway_id', '=', putaway_id.id), ('fixed_location_id', '=', location_putaway_id.id)]
                    line = self.env['stock.fixed.putaway.strat'].search(domain)
                    if not line:
                        putaway_ids |= self.env['stock.fixed.putaway.strat'].create(vals)
        for p_id in putaway_ids:
            print ("-- {} --> {}".format(p_id.product_id.display_name, p_id.fixed_location_id.name))
        xml_id = 'product_putaway.action_stock_fixed_putaway_strat_tree_pp'
        action = self.env.ref(xml_id).read()[0]
        action['domain'] = [('id', 'in', putaway_ids.ids)]
        return action

