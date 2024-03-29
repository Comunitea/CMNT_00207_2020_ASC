# © 2016 Comunitea - Javier Colmenero <javier@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class NotLotName(models.Model):
    _name="not.lot.name"

    name = fields.Char('Nombre no válido')
    product_id = fields.Many2one('product.product', string='Artículo')

class ProductTemplate(models.Model):

    _inherit = "product.template"

    replenish_type = fields.Many2one("variable.replenish", "Replenish type")

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.product_variant_ids.act_not_lot_names()
        return res

class ProductProduct(models.Model):

    _inherit = "product.product"

    not_lot_name_ids = fields.One2many('not.lot.name', 'product_id', string='Lotes no válidos')

    @api.multi
    def act_not_lot_names(self):
        SLN = self.env['not.lot.name']
        for product_id in self.filtered(lambda x: x.tracking != 'none'):
            not_names = product_id.not_lot_name_ids.mapped('name')
            for field in ['default_code', 'wh_code', 'barcode']:
                if product_id[field] and product_id[field] not in not_names:
                    values = {'name': product_id[field], 'product_id': product_id.id}
                    SLN.create(values)

    @api.model
    def create(self, vals):
        ## Esto lo hago para corregir lo de que pone a none el tracking
        if vals.get('product_tmpl_id', False):
            product_tmpl_id = self.env['product.template'].browse(vals['product_tmpl_id'])
            vals['tracking'] = product_tmpl_id.tracking
        ##### HASTA AQUI
        res = super(ProductProduct, self).create(vals)
        res.act_not_lot_names()
        res.create_product_defaults()
        return res

    def create_product_defaults(self):
        try: 
            defaul_stock_location = self.env['ir.config_parameter'].sudo().get_param('product.default_product_location', default=13)
            ## create stock.warehouse.orderpoint
            vals = {'product_id': self.id, 'location_id': 13, 'product_min_qty': 0, 'product_max_qty': 0, 'qty_multiple': 1}
            self.env['stock.warehouse.orderpoint'].create(vals)
            vals = {'putaway_id': 1, 'product_id': self.id, 'fixed_location_id': defaul_stock_location}
            self.env['stock.fixed.putaway.strat'].create(vals)
        except:
            pass

    @api.model
    def cron_variable_replenish(self):
        domain = [
            ("replenish_type", "!=", False),
            ("pack_product", "=", False),
            ("type", "=", "product"),
        ]
        products = self.search(domain)
        products.get_variable_replenish()
        return


    def get_lt_changes(self, lines, offset_days = 0):
        self.ensure_one()
        res = False
        rt = self.replenish_type
        if not rt.use_lt:
            return res
        date_ago = datetime.now() - relativedelta(days=rt.lt_days + offset_days)
        lines = lines.filtered(lambda x: x.create_date >= date_ago)
        total_sales = len(lines.mapped("order_id"))
        if total_sales <= rt.lt_sales:
            res = rt.lt_qty
        return res

    def get_gt_changes(self, lines, offset_days = 0):
        self.ensure_one()
        res = False
        rt = self.replenish_type
        if not rt.use_gt:# or not (rt.gt_sales and rt.gt_days and rt.gt_qty):
            return res
        date_ago = datetime.now() - relativedelta(days=rt.gt_days + offset_days)
        lines = lines.filtered(lambda x: x.create_date >= date_ago)
        total_sales = len(lines.mapped("order_id"))
        if total_sales >= rt.gt_sales:
            res = rt.gt_qty
        return res

    def get_sale_line_by_date(self, days_ago, order="id desc"):
        # current_date = datetime.now().strftime("%Y-%m-%d")
        date_ago = (datetime.now() - relativedelta(days=days_ago)).strftime("%Y-%m-%d")
        sale_domain = [
            ("product_id", "=", self.id),
            ## La fecha de creación del movimiento es la fecha de confirmación de la venta
            ("create_date", ">=", date_ago),
            # ("sale_line_id.order_id.confirmation_date", "<=", current_date),
            ("state", "=", "done"),
            # es mas rapido que el mapped, ya que ahora devolvería todos los movimientos del producto
            ("sale_line_id", "!=", False),
        ]
        return self.env["stock.move"].search(sale_domain, order=order).mapped('sale_line_id')

    def get_variable_replenish(self, max_days = 0 ):

        ## MODIFICO PARA TENER EN CUENTA LOS DÍAS SIN STOCK
        for product in self:
            print ("Product  {}".format(product.display_name))
            rt = product.replenish_type
            if not rt:
                continue

            if not product.orderpoint_ids:
                swo_vals = {'product_id': product.id, 'product_min_qty': 0, 'product_max_qty': 0}
                self.env['stock.warehouse.orderpoint'].create(swo_vals)

            sale_days = max(rt.gt_days, rt.lt_days,rt.sale_days, max_days)

            ## Si hay días sin stock, entonces busco las ventas de los días anteriores que no tengan stock
            if product.qty_available <= 0:
                if product.last_stock_day:
                    days_with_no_stock_count = (fields.date.today()-product.last_stock_day).days
                    print(">>>>>> Se traslada el cálculo a la fecha %s"%product.last_stock_day)
                else:
                    days_with_no_stock_count = 181
                    print(">>>>>> Se traslada el cálculo a la fecha de hace 6 meses")
            else:
                days_with_no_stock_count = 0
            sale_days += days_with_no_stock_count
            lines = product.get_sale_line_by_date(sale_days)
            min_qty = rt.min_qty
            max_qty = rt.max_qty

            min_qty2 = 0
            max_qty2 = 0

            lt_change_qty = product.get_lt_changes(lines, days_with_no_stock_count)
            if lt_change_qty:
                min_qty = lt_change_qty
                max_qty = lt_change_qty

            if not lt_change_qty:
                gt_change_qty = product.get_gt_changes(lines, days_with_no_stock_count)
                if gt_change_qty:
                    min_qty = gt_change_qty
                    max_qty = gt_change_qty

            # COMPUTE ALGORITM MIN MAX
          
            date_ago = datetime.now() - relativedelta(days=rt.sale_days + days_with_no_stock_count)
            sale_lines = lines.filtered(lambda x: x.order_id.confirmation_date >= date_ago).sorted(lambda x:x.order_id.confirmation_date)
          
            total_sales = len(sale_lines.mapped("order_id"))
            total_qty = sum(sale_lines.mapped(rt.qty_field))
            average = 0

            date_ago = datetime.now() - relativedelta(days=30 + days_with_no_stock_count)
            last_month_lines = lines.filtered(lambda x: x.order_id.confirmation_date >= date_ago)
            total_month_sales = len(
                last_month_lines.mapped("order_id")
            )

            # MENOS DE DOS VENTAS ÚLTIMOS 30 DÍAS IMPLICA COGER EL MIN/MAX
            # POR DEFECTO, QUE PUEDE HABE CAMBIADO
            if total_sales and total_month_sales > 2:
                average = (total_qty / total_sales) * rt.average_ratio
                # Get qty by order where qty under average
                for sale_line in sale_lines.filtered(lambda x: x[rt.qty_field] < average):
                    max_qty2 += sale_line[rt.qty_field]
            min_qty2 = max_qty2 * rt.min_qty_ratio

            # UPDATE REPLENISH RULES
            if max_qty and min_qty:
                vals = {
                    "product_min_qty": max(min_qty, min_qty2),
                    "product_max_qty": max(max_qty, max_qty2),
                }
                if product.orderpoint_ids:
                    product.orderpoint_ids.write(vals)
                else:
                    swo = self.env["stock.warehouse.orderpoint"]
                    vals.update(product_id=product.id)
                    swo.create(vals)

    def get_variable_replenish_bis(self, max_days = 0 ):
        for product in self:
            rt = product.replenish_type
            if not rt:
                continue

            if not product.orderpoint_ids:
                swo_vals = {'product_id': product.id, 'product_min_qty': 0, 'product_max_qty': 0}
                self.env['stock.warehouse.orderpoint'].create(swo_vals)

            sale_days = max(rt.gt_days, rt.lt_days,rt.sale_days, max_days)
            lines = product.get_sale_line_by_date(sale_days)
            min_qty = rt.min_qty
            max_qty = rt.max_qty

            min_qty2 = 0
            max_qty2 = 0

            lt_change_qty = product.get_lt_changes(lines)
            if lt_change_qty:
                min_qty = lt_change_qty
                max_qty = lt_change_qty

            if not lt_change_qty:
                gt_change_qty = product.get_gt_changes(lines)
                if gt_change_qty:
                    min_qty = gt_change_qty
                    max_qty = gt_change_qty

            # COMPUTE ALGORITM MIN MAX
          
            date_ago = datetime.now() - relativedelta(days=rt.sale_days)
            sale_lines = lines.filtered(lambda x: x.order_id.confirmation_date >= date_ago).sorted(lambda x:x.order_id.confirmation_date)
          
            total_sales = len(sale_lines.mapped("order_id"))
            total_qty = sum(sale_lines.mapped(rt.qty_field))
            average = 0



            date_ago = datetime.now() - relativedelta(months=1)
            last_month_lines = lines.filtered(lambda x: x.order_id.confirmation_date >= date_ago)
            total_month_sales = len(
                last_month_lines.mapped("order_id")
            )

            # MENOS DE DOS VENTAS ÚLTIMOS 30 DÍAS IMPLICA COGER EL MIN/MAX
            # POR DEFECTO, QUE PUEDE HABE CAMBIADO
            if total_sales and total_month_sales > 2:
                average = (total_qty / total_sales) * rt.average_ratio
                # Get qty by order where qty under average
                for sale_line in sale_lines.filtered(lambda x: x[rt.qty_field] < average):
                    max_qty2 += sale_line[rt.qty_field]
            min_qty2 = max_qty2 * rt.min_qty_ratio

            # UPDATE REPLENISH RULES
            if max_qty and min_qty:
                vals = {
                    "product_min_qty": max(min_qty, min_qty2),
                    "product_max_qty": max(max_qty, max_qty2),
                }
                if product.orderpoint_ids:
                    product.orderpoint_ids.write(vals)
                else:
                    swo = self.env["stock.warehouse.orderpoint"]
                    vals.update(product_id=product.id)
                    swo.create(vals)
