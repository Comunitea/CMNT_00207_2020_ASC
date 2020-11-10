
from odoo import api, fields, models
from odoo.fields import first


class StockMoveLocationWizard(models.TransientModel):
    _inherit = "wiz.stock.move.location"

    product_ids = fields.Many2many('product.product', string='Products')

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
