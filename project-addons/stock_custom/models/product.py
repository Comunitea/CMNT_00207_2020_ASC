# -*- coding: utf-8 -*-
# © 2016 Comunitea - Javier Colmenero <javier@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ProductProduct(models.Model):

    _inherit = 'product.product'

    replenish_type = fields.Many2one(
        'variable.replenish', 'Replenish type')
    
    @api.model
    def cron_variable_replenish(self):
        domain = [('replenish_type', '!=', False)]
        products = self.search(domain)
        products.get_variable_replenish()
        return

    def get_moves_by_date(self, days_ago):
        self.ensure_one()
        current_date = datetime.now().strftime('%Y-%m-%d')
        date_ago = (datetime.now() - relativedelta(days=days_ago)).\
            strftime('%Y-%m-%d')
        domain = [
            ('product_id', '=', self.id),
            ('picking_id.date_done', '>=', date_ago),
            ('picking_id.date_done', '<=', current_date),
            ('picking_id.state', 'in', ['done']),
            ('sale_line_id', '!=', False),
        ]
        moves = self.env['stock.move'].search(domain)
        return moves
    
    def get_lt_changes(self):
        self.ensure_one()
        res = False
        rt = self.replenish_type
        if not rt.use_lt or not (rt.lt_sales and rt.lt_days and rt.lt_qty):
            return res
        
        moves = self.get_moves_by_date(rt.lt_days)
        total_sales = len(moves.mapped('sale_line_id.order_id'))
        if total_sales <= rt_lt_sales:
            res = rt.lt_qty
        return res
    
    def get_gt_changes(self):
        self.ensure_one()
        res = False
        rt = self.replenish_type
        if not rt.use_gt or not (rt.gt_sales and rt.gt_days and rt.gt_qty):
            return res
        
        moves = self.get_moves_by_date(rt.gt_days)
        total_sales = len(moves.mapped('sale_line_id.order_id'))
        if total_sales >= rt_gt_sales:
            res = rt.gt_qty
        return res

    def get_variable_replenish(self):
        for product in self:
            rt = product.replenish_type
            if not rt:
                continue

            min_qty = rt.min_qty
            max_qty = rt.max_qty
            min_qty2 = 0
            max_qty2 = 0

            lt_change_qty = product.get_lt_changes()
            if lt_change_qty:
                min_qty = lt_change_qty
                max_qty = lt_change_qty
            
            if not lt_change_qty:
                gt_change_qty = product.get_gt_changes()
                if gt_change_qty:
                    min_qty = gt_change_qty
                    max_qty = gt_change_qty

                # COMPUTE ALGORITM MIN MAX
                moves = self.get_moves_by_date(rt.sale_days)
                order_qtys = {}
                total_sales = len(moves.mapped('sale_line_id.order_id'))
                total_qty = sum(moves.mapped('sale_line_id.qty_delivered'))

                average = (total_qty / total_sales) * rt.average_ratio
                # Get qty by order where qty under average
                for move in moves:
                    if move.product_uom_qty < average:
                        if move.sale_line_id.qty_delivered:
                            sale = move.sale_line_id.order_id
                            if sale not in order_qtys:
                                order_qtys[sale] = 0
                            order_qtys[sale] += move.sale_line_id.qty_delivered
                
                if not order_qtys:
                    continue
                    
                max_qty2 = sum(order_qtys.values())
                min_qty2 = max_qty2 * rt.min_qty_ratio

            # UPDATE REPLENISH RULES
            if max_qty and min_qty:
                vals = {
                    'product_min_qty': max(min_qty, min_qty2),
                    'product_max_qty': max(max_qty, max_qty2)
                }
                if product.orderpoint_ids:
                    product.orderpoint_ids.write(vals)
                else:
                    swo = self.env['stock.warehouse.orderpoint']
                    vals.update(product_id=product.id)
                    swo.create(vals)