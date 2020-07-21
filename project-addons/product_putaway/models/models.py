# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models, fields, _


class StockPicking(models.Model):

    _inherit = "stock.picking"

    @api.multi
    def update_new_product_putaway(self):

        product_ids = (
            self.filtered(lambda x: x.state == "done")
            .mapped("move_lines")
            .mapped("product_id")
        )
        warehouse_ids = self.mapped("picking_type_id").mapped("warehouse_id")
        return product_ids._compute_putaway_from_stock(warehouse_ids)


class StockPickingBatch(models.Model):

    _inherit = "stock.picking.batch"

    @api.multi
    def update_new_product_putaway(self):
        warehouse_ids = (
            self.mapped("picking_ids").mapped("picking_type_id").mapped("warehouse_id")
        )
        product_ids = (
            self.mapped("move_lines")
            .filtered(lambda x: x.state == "done")
            .mapped("product_id")
        )
        return product_ids._compute_putaway_from_stock(warehouse_ids)


class StockInventory(models.Model):

    _inherit = "stock.inventory"

    @api.multi
    def update_new_product_putaway(self):

        product_ids = self.mapped("move_ids").mapped("product_id")
        return product_ids._compute_putaway_from_stock()
