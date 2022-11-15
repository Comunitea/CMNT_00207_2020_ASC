##############################################################################
#
#    Copyright (C) 2015 Pexego All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api, exceptions, _


class WzdIncomingProduct(models.TransientModel):
    _name = "wzd.incoming.product"

    with_available_stock = fields.Boolean("With available stock", default=False, help="Negative forecast quantity")
    with_incoming_moves = fields.Boolean("With incoming purchases", default=True, help="With incoming purchases")
    category_ids = fields.Many2many("product.category", string="Categories")
    product_ids = fields.Many2many("product.template", string="Products")


    @api.multi
    def show_incoming_product(self):
        product_ids = self.env['product.template']
        domain = [('type', '=', 'product'), ('default_on', '=', True)]
        tmpl_ids_all = []
        product_ids_all = []
        if self.category_ids:
            cat_ids = self.category_ids + self.category_ids.mapped('child_id')
            sql = "select product_id from product_categ_rel where categ_id in (%s)"%','.join(str(x) for x in cat_ids.ids)
            self._cr.execute(sql)
            res = self._cr.fetchall()
            tmpl_ids_all += [x[0] for x in res]
            print("Se van a filtrar %s artículos" % len(res))
        if self.product_ids:
            tmpl_ids_all += self.product_ids.ids
            print("Se van a filtrar %s artículos" % len(self.product_ids))
        if self.with_incoming_moves:
            incoming_domain = self.env['product.product'].get_domain_for_incoming_qtys()
            if tmpl_ids_all:
                incoming_domain += [('product_id.product_tmpl_id', 'in', tmpl_ids_all)]
            product_ids = self.env['stock.move'].search_read(incoming_domain, ['product_id'])
            print("Se van a filtrar por %s movimientos " % len(self.product_ids))
            tmpl_ids_all = []
            product_ids_all += [x['product_id'][0] for x in product_ids]

        if tmpl_ids_all:
            # tmpl_ids =  [x for x in tmpl_ids_all] # "[%s]"%','.join(str(x) for x in tmpl_ids_all)
            domain += [('product_tmpl_id', 'in', [x for x in tmpl_ids_all])]
        elif product_ids_all:
            # product_ids = [x for x in product_ids_all] #   "[%s]"%','.join(str(x) for x in product_ids_all)
            domain += [('id', 'in', [x for x in product_ids_all])]
        print("Búsqueda sin stock")
        product_ids = self.env['product.product'].search_read(domain, ['id'])
        print(">>> OK. %d registros "%len(product_ids))
        if not self.with_available_stock:
            print("Búsqueda con stock")
            domain += [('virtual_available', '<=', 0)]
            product_ids = self.env['product.product'].search_read(domain, ['id'])
            print(">>> OK. %d registros "%len(product_ids))
        p_ids = []
        for p_id in product_ids:
            p_ids += [p_id['id']]

        product_id = self._context.get('product_id', False)
        tree_view = self.env.ref('product_expected_incoming_date.view_incoming_product_tree')
        action = self.env.ref('stock.stock_product_normal_action').read()[0]
        action['view_id'] =  tree_view.id
        action['views'] = [(tree_view.id, 'tree')]
        action['view_mode'] =  'tree'
        action["domain"] = [('id', 'in', p_ids)]
        
        action["context"] = {
            'hide_product': False,
        }
        return action
