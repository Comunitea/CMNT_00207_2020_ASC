# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)



class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def _compute_tracking_count(self):
        for templ_id in self:
            templ_id.tracking_count = sum(x.tracking_count for x in self.product_variant_ids)

    @api.multi
    @api.depends('tracking', 'virtual_tracking')
    def _compute_template_tracking(self):
        for template in self:
            if template.virtual_tracking:
                template.template_tracking = 'virtual'
            else:
                template.template_tracking = template.tracking

    virtual_tracking = fields.Boolean(
        "With tracking", help="Alternative tracking for products with tracking = 'none'"
    )
    tracking_count = fields.Integer(
        "Tracking serial count", compute=_compute_tracking_count
    )
    template_tracking = fields.Selection(selection=[
        ('virtual', 'Nº Serie Virtual'),
        ('serial', 'Nº Serie'),
        ('lot', 'Lote'),
        ('none', 'Sin seguimiento')],
         string='Product Tracking',store=True, compute=_compute_template_tracking)

    @api.multi
    def action_view_serials(self):

        action = self.env.ref("stock.action_production_lot_form").read()[0]
        action["context"] = {"product_id": self.id}
        domain = self.product_variant_ids.get_lot_domain()
        res = self.env["stock.production.lot"].search_read(domain, ["id"])
        action['context']={'default_product_id': self.id,
                           'default_virtual_tracking': self.virtual_tracking}
        if res:
            ids = [x["id"] for x in res]
            action["domain"] = [("id", "in", ids)]
        else:
            action["domain"] = [('id', 'in', [])]
        return action


    @api.onchange("tracking")
    def onchange_tracking(self):
        self.virtual_tracking = False
        return super().onchange_tracking()


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def _compute_tracking_count(self):
        tracking_ids = self.filtered(lambda x: x.template_tracking != 'none')
        for product_id in tracking_ids:
            domain = product_id.get_lot_domain()
            product_id.tracking_count = self.env["stock.production.lot"].search_count(
                domain
            )
        (self - tracking_ids).write({'tracking_count': 0})

    tracking_count = fields.Integer("Tracking serial count", compute=_compute_tracking_count)
    template_tracking = fields.Selection(related='product_tmpl_id.template_tracking', store=True)

    @api.multi
    def action_view_serials(self):
        action = self.env.ref("stock.action_production_lot_form").read()[0]

        domain = self.get_lot_domain()
        res = self.env["stock.production.lot"].search_read(domain, ["id"])
        action['context']={'default_product_id': self.id,
                           'default_virtual_tracking': self.virtual_tracking}
        if res:
            ids = [x["id"] for x in res]
            action["domain"] = [("id", "in", ids)]
        else:
            action["domain"] = [('id', 'in', [])]
        return action

    def _get_lot_domain_for_virtual(self, location_id=False, strict=False, lot_names = []):
        if not location_id:
            location_id = self.env.ref('stock.stock_location_stock')
        if strict:
            operator = '='
        else:
            operator = 'child_of'
 
        if len(self) == 1:
            domain = [('product_id', '=', self.id)]
        else:
            domain = [('product_id', 'in', self.ids)]

        domain += [("real_location_id", operator, location_id.id)]
        if lot_names:
            domain += [("name", "in", lot_names)]

        return domain
    
    
    ## Esta función devuelve los lotes disponibles en una ubicación para un artículo
    def get_lot_domain(self, location_id=False, lot_names=False, strict=False,stock=True):
        self.ensure_one()
        if not location_id:
            location_id = self.env.ref('stock.stock_location_stock')
        if strict:
            operator = '='
        else:
            operator = 'child_of'
        domain = [('product_id', '=', self.id)]
        
        if self.virtual_tracking:
            ## TODO REVISAR
            domain += [("real_location_id", operator, location_id.id)]
        else:
            domain += [('quant_ids.location_id', operator, location_id.id)]
        if stock:
            domain += [('quant_ids.quantity', '>', 0)]
        if lot_names:
            domain = expression.AND ([domain, [("name", "in", lot_names)]])
        return domain
      
    def check_quant_reserved_quantity(self):
        ##Esta función ajusta la cantidad disponible a la reservas hechas
        Quant = self.sudo().env['stock.quant']
        for product in self:
            domain = [('product_id', '=', product.id), ('reserved_quantity', '>', 0)]
            assigned_sml = [('product_id', '=', product.id), ('state', 'in', ['assigned', 'partially_available'])]
            sml_ids = self.env['stock.move.line'].search(assigned_sml, order="state asc, create_date")
            ## Quito todas las reservas y las pongo a 0
            Quant.search(domain).write({'reserved_quantity': 0})
            for sml_id in sml_ids:
                domain = [
                    ('product_id', '=', sml_id.product_id.id),
                    ('location_id', '=', sml_id.location_id.id),
                    ('lot_id', '=', sml_id.lot_id and sml_id.lot_id.id or False)]
                quant_id = Quant.search(domain)
                free_qty = quant_id.quantity - quant_id.reserved_quantity
                if sml_id.product_uom_qty <= free_qty:
                    quant_id.reserved_quantity += sml_id.product_uom_qty
                    sml_ids -= sml_id
            if sml_ids:
                sml_ids.with_context(bypass_reservation=True).unlink()
