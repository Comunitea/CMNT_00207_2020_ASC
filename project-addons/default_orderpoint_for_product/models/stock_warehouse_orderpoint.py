
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.osv import expression

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def unlink_mts_mto_from_template(self):
        self._cr.execute("delete from stock_route_product where route_id = 11")


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.multi
    def create_auto_swo(self):
        """
        Crea SWO para los sioguientes casos:
        Opcion 1
            Sin variantes. No bom_id. No Bajo Pedido.
        
        Opcion 2
            Variante. No bom id para esta variante. No bajo pedido.
        """
        Product = self.env['product.product']
        Template = self.env['product.template']

        # Productos que ya tienen un orderpoint
        # para variantes
        # Dominio para variantes (+ de 1 atributo) sin mrp_bom
        variant_domain = [('product_tmpl_id.attribute_line_ids', '!=', False)]
        pt_bom_domain = [('product_tmpl_id.bom_ids', '=', False)]
        variantes_con_bom_ids = expression.AND ([variant_domain, pt_bom_domain])
        variant_ids = Product.search(variantes_con_bom_ids)
        print ("DEBERÍA SER SIEMPRE VACIO %s" % variant_ids)
        #Para plantillas
        template_domain = [('product_tmpl_id.attribute_line_ids', '=', False)]
        #pp_bom_domain = [('variant_bom_ids', '=', False)]
        template_con_bom_ids = expression.AND ([template_domain, pt_bom_domain])
        #template_ids = Product.search(template_con_bom_ids)
        
        # DOminio de todos los productos que no tengan bom ni orderpoint
        pp_domain = expression.OR ([variantes_con_bom_ids, template_con_bom_ids])
        # Además el producto debe estar marcado como comprar y NO mts mto. Podría estar bajo pedido pero entonces no puede/debería estar como comprar
        buy_domain = [('route_ids.rule_ids.action', '=', 'buy')]

        # y no tiene que tener una orden ya creada
        no_swo_domain = [('orderpoint_ids', '=', False)]
        type_domain = [('type', '=', 'product')]
        complete_domain = expression.AND ([type_domain, no_swo_domain, buy_domain, pp_domain])
        for product_id in Product.search(complete_domain)[:10]:
            swo_vals = {'product_id': product_id.id, 'product_min_qty': 0, 'product_max_qty': 0}
            swo_id = self.env['stock.warehouse.orderpoint'].create(swo_vals)
            swo_id.name = '%s *'% swo_id.name
            print ("Nueva regla: %s"%swo_id.name)
        

    