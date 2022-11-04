# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)


TRACKING_VALUES = [
        ('virtual', 'Nº Serie Virtual'),
        ('serial', 'Nº Serie'),
        ('lot', 'Lote'),
        ('none', 'Sin seguimiento')]

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
    template_tracking = fields.Selection(selection=TRACKING_VALUES,
         string='Product Tracking', compute=_compute_template_tracking ,store=True)

    @api.multi
    def action_view_serials(self):

        action = self.env.ref("stock.action_production_lot_form").read()[0]
        action["context"] = {"product_id": self.id}
        domain = self.product_variant_ids.get_serial_domain()
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

    @api.multi
    def mig_to_virtual(self):
        domain = [('tracking', '=', 'none')]
        self.env['product.template'].search(domain).write({'template_tracking': 'none' })
        domain = [('tracking', '=', 'lot')]
        self.env['product.template'].search(domain).write({'template_tracking': 'lot' })
        domain = [('tracking', '=', 'serial')]
        self.env['product.template'].search(domain).write({'template_tracking': 'serial' })
        
    @api.multi
    def change_to_virtual(self):
        for template in self:
            template.tracking = 'none'
            template.virtual_tracking = True
            template.template_tracking = 'virtual'
            move_ids = self.env['stock.move']
            for product_id in template.product_variant_ids:
                ## Los movimientos hechos les paso lot_id a serial_ids
                domain = [('product_id', '=', product_id.id), ('lot_id', '!=', False), ('state', '=', 'done')]
                sml_ids = self.env['stock.move.line'].search(domain)
                _logger.info("Borrando series y actualizando de %d movimientos"%len(sml_ids))
                if sml_ids:
                    for sml in sml_ids:
                        sml.serial_ids = [(6, 0, [sml.lot_id.id])]
                    #    sml.lot_id = False
                    ## Los no hechos los borro
                domain = [('product_id', '=', product_id.id), ('state', 'in', ['assigned', 'partially_available'])]
                move_ids = self.env['stock.move.line'].search(domain).mapped('move_id')
                _logger.info("Quitando reservas para %s"%product_id.display_name)
                sql = "delete from stock_move_line where product_id = %d and state in ('assigned', 'partially_available')"%product_id.id
                self.env.cr.execute(sql)
                _logger.info("Quitando lot_id en quant para %s"%product_id.display_name)
                sql = "update stock_quant set lot_id = null where product_id = %d"%product_id.id
                self.env.cr.execute(sql)
                _logger.info("Mezclando quants para %s"%product_id.display_name)
                query = """WITH
                            dupes AS (
                                SELECT min(id) as to_update_quant_id,
                                    (array_agg(id ORDER BY id))[2:array_length(array_agg(id), 1)] as to_delete_quant_ids,
                                    SUM(reserved_quantity) as reserved_quantity,
                                    SUM(quantity) as quantity,
                                    MIN(in_date) as in_date
                                FROM stock_quant
                                where product_id=%d
                                GROUP BY product_id, company_id, location_id, lot_id, package_id, owner_id
                                HAVING count(id) > 1
                            ),
                            _up AS (
                                UPDATE stock_quant q
                                    SET quantity = d.quantity,
                                        reserved_quantity = d.reserved_quantity,
                                        in_date = d.in_date
                                FROM dupes d
                                WHERE d.to_update_quant_id = q.id
                            )
                    DELETE FROM stock_quant WHERE id in (SELECT unnest(to_delete_quant_ids) from dupes)
                """%product_id.id
                try:
                    with self.env.cr.savepoint():
                        self.env.cr.execute(query)
                except:
                    _logger.info('an error occured while merging quants')
                _logger.info("Reservas de quants a 0 para  %s"%product_id.display_name)
                sql = "update stock_quant set reserved_quantity = 0 where product_id = %d"%product_id.id
                self.env.cr.execute(sql)
                self.env.cr.commit()
                domain = [('product_id', '=', product_id.id)]
                serial_ids = self.env['stock.production.lot'].search(domain)
                if serial_ids:
                    serial_ids.update_real_location_id()
                if move_ids:
                    _logger.info("Resrvando de nuevo los movimientos para  %s"%product_id.display_name)
                    move_ids.write({'state': 'confirmed'})
                    move_ids._action_assign()
                _logger.info("FIANLIZADO  %s"%product_id.display_name)
        

class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def _compute_tracking_count(self):
        tracking_ids = self.filtered(lambda x: x.template_tracking != 'none')
        for product_id in tracking_ids:
            domain = product_id.get_serial_domain()
            product_id.tracking_count = self.env["stock.production.lot"].search_count(
                domain
            )
        (self - tracking_ids).write({'tracking_count': 0})

    tracking_count = fields.Integer("Tracking serial count", compute=_compute_tracking_count)
    # template_tracking = fields.Selection(related='product_tmpl_id.template_tracking')#, store=True)
    # virtual_tracking = fields.Boolean(related='product_tmpl_id.virtual_tracking')#, store=True)


    @api.multi
    def action_view_serials(self):
        action = self.env.ref("stock.action_production_lot_form").read()[0]
        domain = self.get_serial_domain()
        res = self.env["stock.production.lot"].search_read(domain, ["id"])
        action['context']={'default_product_id': self.id,
                           'default_virtual_tracking': self.virtual_tracking}
        if res:
            ids = [x["id"] for x in res]
            action["domain"] = [("id", "in", ids)]
        else:
            action["domain"] = [('id', 'in', [])]
        return action
    
    ## Esta función devuelve los nº de serie  disponibles en una ubicación para un artículo
    def get_serial_domain(self, location_id=False, lot_names=False, strict=False):
        self.ensure_one()
        if not location_id:
            location_id = self.env.ref('stock.stock_location_stock')
        if strict:
            operator = '='
        else:
            operator = 'child_of'
        domain = [('product_id', '=', self.id)]
        domain += [("real_location_id", operator, location_id.id)]
        if lot_names:
            domain = expression.AND ([domain, [("name", "in", lot_names)]])
        _logger.info("Lot domain: %s"%domain)
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

        
    @api.multi
    def change_to_virtual(self):
        return self.mapped('product_tmpl_id').change_to_virtual()
    