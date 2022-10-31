# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.addons.queue_job.job import job

class ProductProduct(models.Model):

    _inherit = "product.product"
    pack_product = fields.Boolean(compute="_compute_pack_product", store=True)
    need_export_stock = fields.Boolean()

    @api.multi
    def update_prestashop_qty(self):
        if self._context.get("cron_compute"):
            self.write({"need_export_stock": False})
            for prod in self:
                if prod.used_in_bom_count:
                    boms = self.env["mrp.bom"].search(
                        [("bom_line_ids.product_id", "=", prod.id)]
                    )
                    self = (
                        self
                        + boms.mapped("product_tmpl_id.product_variant_ids")
                        + boms.mapped("product_id")
                    )
            return super().update_prestashop_qty()
        else:
            self.write({"need_export_stock": True})

    @api.depends("attribute_value_ids.product_id")
    def _compute_pack_product(self):
        for product in self:
            if any(product.mapped("attribute_value_ids.product_id")) or self.env[
                "mrp.bom"
            ]._bom_find(product=product):
                product.pack_product = True
            else:
                product.pack_product = False
            # product.update_prestashop_qty()

    def recompute_packs(self):
        for product in self:
            create_bom = False
            bundle_products = {}
            for attr_value in product.attribute_value_ids:
                if attr_value.product_id:
                    bundle_products[attr_value.product_id] = 1
            if bundle_products:
                base_product = product.product_tmpl_id.product_variant_ids.filtered(
                    lambda r: not r.mapped("attribute_value_ids.product_id")
                )
                if base_product:
                    bundle_products[base_product[0]] = 1
                product_bom = self.env["mrp.bom"].search(
                    [("product_id", "=", product.id)]
                )
                if product_bom:
                    current_bom = product_bom
                    for line in current_bom.bom_line_ids:
                        if (
                            line.product_id not in bundle_products.keys()
                            or line.product_qty != bundle_products[line.product_id]
                        ):
                            product_bom.write({"active": False})
                            create_bom = True
                            break
                    for in_product in bundle_products.keys():
                        if in_product not in current_bom.mapped(
                            "bom_line_ids.product_id"
                        ):
                            product_bom.write({"active": False})
                            create_bom = True
                            break
                else:
                    create_bom = True
                if create_bom:
                    self.env['stock.warehouse.orderpoint'].search(
                        [('product_id', '=', product.id)]).unlink()
                    self.env["mrp.bom"].create(
                        {
                            "product_tmpl_id": product.product_tmpl_id.id,
                            "product_id": product.id,
                            "type": "phantom",
                            "bom_line_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": x.id,
                                        "product_qty": bundle_products[x],
                                    },
                                )
                                for x in bundle_products.keys()
                            ],
                        }
                    )

    def _compute_virtual_stock_conservative(self):
        pack_prods = self.filtered(lambda r: r.pack_product)
        not_pack_prods = self.filtered(lambda r: not r.pack_product)
        res = super(
            ProductProduct, not_pack_prods
        )._compute_virtual_stock_conservative()
        for prod in pack_prods:
            bom = self.env["mrp.bom"]._bom_find(product=prod)
            min_qty = 9999999999999
            if bom and bom.type == "phantom":
                for line in bom.bom_line_ids:
                    available = line.product_id.virtual_stock_conservative
                    pack_quantity = available / line.product_qty
                    if pack_quantity < min_qty:
                        min_qty = pack_quantity
                    if min_qty == 0:
                        break
                prod.virtual_stock_conservative = int(min_qty)
        return res

    @api.multi
    def _compute_qty_available_not_reserved(self):
        pack_prods = self.filtered(lambda r: r.pack_product)
        not_pack_prods = self.filtered(lambda r: not r.pack_product)
        res = super(
            ProductProduct, not_pack_prods
        )._compute_qty_available_not_reserved()
        for prod in pack_prods:
            bom = self.env["mrp.bom"]._bom_find(product=prod)
            min_qty = 9999999999999
            if bom and bom.type == "phantom":
                for line in bom.bom_line_ids:
                    available = line.product_id.qty_available_not_res
                    pack_quantity = available / line.product_qty
                    if pack_quantity < min_qty:
                        min_qty = pack_quantity
                    if min_qty == 0:
                        break
                prod.qty_available_not_res = int(min_qty)
        return res

    def create(self, vals):
        res = super().create(vals)
        standard_price_added = False
        if isinstance(vals, dict) and vals.get("standard_price"):
            standard_price_added = True
        elif isinstance(vals, list) and any([x.get("standard_price") for x in vals]):
            standard_price_added = True
        if standard_price_added:
            for record in self.mapped("product_tmpl_id"):
                self.env["product.template"]._event("on_standard_price_changed").notify(
                    record
                )
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get("standard_price"):
            for record in self.mapped("product_tmpl_id"):
                self.env["product.template"]._event("on_standard_price_changed").notify(
                    record
                )
        return res


class PrestashopProductCombination(models.Model):
    _inherit = 'prestashop.product.combination'

    @job(default_channel='root.prestashop')
    def export_inventory(self, fields=None):
        """ Export the inventory configuration and quantity of a product. """
        backend = self.backend_id
        if not backend.backend_export_qty:
            return True
        with backend.work_on('prestashop.product.combination') as work:
            exporter = work.component(usage='inventory.exporter')
            return exporter.run(self, fields)