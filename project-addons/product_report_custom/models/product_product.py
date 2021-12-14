# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)
DAYS = 180

class DaysWithNoStock(models.Model):
    _name = "days.no.stock"
    order = "date desc"
    product_id = fields.Many2one('product.product', string='Artículo')
    tmpl_id = fields.Many2one('product.template', string='Artículo')
    date = fields.Date('Date')
    qty_available= fields.Float('Qty', default=0)

    _sql_constraints = [(
        'product_date_unique',
        'unique(product_id, date)',
        'No puedes tener 2 registros para mismo artículo y fecha!'
        )]
    
    def get_no_stock_days_at_date(self, to_date=False,product_ids=False):
       
        if not product_ids:
            p_domain = ['|', ('active', '=', True),('active', '=', False)]
        else:
            p_domain = [('id', 'in', product_ids.ids)]
        ctx = self._context.copy()
        if to_date:
            ctx.update(to_date=to_date)
        else:
            to_date = fields.Date.from_string(fields.Date.today())
        
        product_ids = self.env['product.product'].with_context(ctx).search(p_domain)
        _logger.info (">>>>>>>>>>>>>>>>>>>>%s %d"%(to_date, len(product_ids)))
        cont = len(product_ids)

        for product in product_ids:
            #_logger.info (">>>>>>>>>>>>>>>>>%s>>>%s %d"%(to_date, product.display_name, cont))
            cont -=1
            vals = {'product_id': product.id, 
                    'tmpl_id': product.product_tmpl_id.id, 
                    'date': to_date, 
                    'qty_available': product.qty_available,
                    }
            self.env['days.no.stock'].create(vals)
            

    def get_all_no_stock_days(self):
        ## Solo se ejecuta una vez.
        self.env['days.no.stock'].search([]).unlink()
        self._get_all_no_stock_days()

    def _get_all_no_stock_days(self, product_ids= False):
        ## Revisa todos los días por si alguno no se lanzó el cron. Si hay algun registro es que se lanzó.
        _days = DAYS
        ctx = self._context.copy()
        while _days >1:
            to_date = fields.Datetime.to_string(fields.Date.today()- relativedelta(days=_days))
            domain = [('date', '=', to_date)]
            if product_ids:
                domain += [('product_id', 'in', product_ids.ids)]
            if not self.search(domain, limit=1):
                _logger.info (">>>>>>>>>>>>>>>>>>>>Generando no stock days para %s "%to_date)
                self.get_no_stock_days_at_date(to_date, product_ids)
            _days -= 1

    @api.multi
    def compute_days_with_no_stock(self, product_ids = False):
        ## DIARIO
        today_date = fields.Date.from_string(fields.Date.today())
        ## Borro los anteriores a 180 días
        last_date = today_date - relativedelta(days=DAYS)
        domain = ['|', ('date', '=', today_date), ('date', '<', last_date)]
        _logger.info (">>>>> Borrando anteriores ....")
        if product_ids:
            domain = [('product_id', 'in', product_ids.ids)] + domain
        self.env['days.no.stock'].search(domain).unlink()
        ## Creo los de hoy
        _logger.info (">>>>> Genrando para hoy")
        self.get_no_stock_days_at_date(False, product_ids)
        _logger.info (">>>>> Genrando anteriores perdidos")
        self._get_all_no_stock_days(product_ids)
        if not product_ids:
            p_domain = ['|', ('active', '=', True),('active', '=', False)]
            product_ids = self.env['product.product'].search(p_domain)
        for product in product_ids:
            days_with_no_stock_ids = product.days_with_no_stock_ids.filtered(lambda x: not x.qty_available)
            days_with_stock_ids = product.days_with_no_stock_ids.filtered(lambda x: x.qty_available)
            product.days_with_no_stock_count = len(days_with_no_stock_ids)
            product.last_no_stock_day = days_with_no_stock_ids and days_with_no_stock_ids[-1].date or False
            product.last_stock_day = days_with_stock_ids and days_with_stock_ids[-1].date or False
            
class ProductAlarmDays(models.Model):
    _name = "product.alarm.days"
    _rec_name = "code"

    code = fields.Char("Code")
    days = fields.Integer("# Days")

    @api.multi
    def name_get(self):
        res = []
        for alarm in self:
            name = "{}: {} days".format(alarm.code, alarm.days)
            res.append((alarm.id, name))
        return res


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def compute_days_with_no_stock(self):
        for template in self:
            template.days_with_no_stock_count = len(template.days_with_no_stock_ids)
            

    count_sales = fields.Char("Count sales")
    count_sales_0 = fields.Float(string="Count sales 0")
    count_sales_1 = fields.Float(string="Count sales 1")
    count_sales_2 = fields.Float(string="Count sales 2")
    count_sales_3 = fields.Float(string="Count sales 3")
    days_with_sales = fields.Boolean(string="Sale alarm day")
    days_for_alarm = fields.Many2one("product.alarm.days", string="Days for sale alarm")
    days_with_no_stock_count = fields.Integer('Days with no stock count') #, compute=compute_days_with_no_stock)
    days_with_no_stock_ids = fields.One2many('days.no.stock', 'tmpl_id',  string='Days with no stock')
    last_no_stock_day = fields.Date('Day with stock=0', help ="Ultimo día sin stock")
    last_stock_day = fields.Date('Day with stock', help ="Ultimo día con stock")


    @api.multi
    def compute_product_template_sales(self):
        if not self:
            self = self.search([])
        self._compute_product_template_sales()
        self._compute_product_template_sale_alarm()

    @api.multi
    def _compute_product_template_sales(self):
        product_ids = self.mapped("product_variant_ids")
        product_ids._compute_product_sales()
        for template in self:
            for i in range(0, 4):
                field = "count_sales_{}".format(i)
                template[field] = sum(x[field] for x in template.product_variant_ids)

        for template in self:
            month_str = "{}".format(template["count_sales_0"])
            for i in range(1, 4):
                month_str = "{}/{}".format(
                    month_str, template["count_sales_{}".format(i)]
                )
                template.count_sales = month_str

    @api.multi
    def _compute_product_template_sale_alarm(self):
        self.mapped("product_variant_ids")._compute_product_sale_alarm()
        for template in self:
            template.days_with_sales = any(
                x.days_with_sales for x in template.product_variant_ids
            )


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def compute_days_with_stock_count(self):
        for product in self:
            product.days_with_no_stock_count = len(product.days_with_no_stock_ids)
       
    count_sales = fields.Char("Count sales")
    count_sales_0 = fields.Float(string="Count sales 0")
    count_sales_1 = fields.Float(string="Count sales 1")
    count_sales_2 = fields.Float(string="Count sales 2")
    count_sales_3 = fields.Float(string="Count sales 3")
    days_with_sales = fields.Boolean(string="Sale alarm day")
    days_for_alarm = fields.Many2one("product.alarm.days", string="Days for sale alarm")
    days_with_no_stock_count = fields.Integer('Days with no stock count')
    days_with_no_stock_ids = fields.One2many('days.no.stock', 'product_id', string='Days with no stock')
    

    @api.multi
    def compute_product_sales(self):
        if not self:
            self = self.search([])
        self._compute_product_sales()

    @api.multi
    def compute_days_with_no_stock(self):
        self.env['days.no.stock'].compute_days_with_no_stock(self)

    @api.multi
    def _compute_product_sales(self):
        if len(self)> 1:
            _where =  ' and  product_id in {}'.format((tuple(self.ids)))
        elif len(self) == 1:
            _where =  ' and  product_id = {}'.format(self.id)
        else: 
            _where = ''

        domain = [("key", "ilike", "count_sales_")]
        count = dict(
            (item["key"], int(item["value"]))
            for item in self.env["ir.config_parameter"].search_read(
                domain, ["key", "value"]
            )
        )

        interval_0 =  count.get("count_sales_0", 1)
        interval_1 =  count.get("count_sales_1", 2)
        interval_2 =  count.get("count_sales_2", 3)
        interval_3 =  count.get("count_sales_3", 6)

        sql ="""
            with grouped as (
            select 
                case when sl.usage = 'internal' then product_uom_qty 
                else product_uom_qty * -1
                end quantity,
                product_uom_qty, sm.id, sl.usage, product_id, now(), 
                now() - interval '{} month' < sm.date as ventas_0,
                now() - interval '{} month' < sm.date as ventas_1,
                now() - interval '{} month' < sm.date as ventas_2,
                now() - interval '{} month' < sm.date as ventas_3
                from stock_move sm
                join stock_location sl on sm.location_id = sl.id
                join stock_location sl2 on sm.location_dest_id = sl2.id
                where state = 'done' and (now() - interval '6 month') < sm.date {}
                and ((sl.usage = 'internal' and sl2.usage = 'customer') or (sl.usage = 'customer' and sl2.usage = 'internal') )
                order by date
            )
            select sum(quantity) as quantity, product_id, ventas_0, ventas_1, ventas_2, ventas_3
            from grouped 
            group by product_id, ventas_0, ventas_1, ventas_2, ventas_3
            order by product_id
            """.format(interval_0, interval_1,interval_2, interval_3, _where)
        self._cr.execute(sql)
        res = self._cr.fetchall()
        
        product_ids = {}
        for product in self:
            product_ids[product.id] = {'count_sales_0': 0, 'count_sales_1': 0, 'count_sales_2': 0, 'count_sales_3': 0}
        total = len(self)
        _logger.info("Número de articulos: {}".format(total))
        for item in res:
            quantity = item[0]
            product_id = item[1]
            ventas_0 = item[2]
            ventas_1 = item[3]
            ventas_2 = item[4]
            ventas_3 = item[5]
            if ventas_0: 
                product_ids[product_id]['count_sales_0'] += quantity
            if ventas_1: 
                product_ids[product_id]['count_sales_1'] += quantity
            if ventas_2: 
                product_ids[product_id]['count_sales_2'] += quantity
            if ventas_3: 
                product_ids[product_id]['count_sales_3'] += quantity
        
        while self:
            _logger.info ('Faltan %d'%total)
            rg = self[:100]
            
            for product in rg:
                total -= 1
                _logger.info ('%s'%product.display_name)
                vals = {
                    'count_sales_0': product_ids[product.id]['count_sales_0'],
                    'count_sales_1': product_ids[product.id]['count_sales_1'],
                    'count_sales_2': product_ids[product.id]['count_sales_2'],
                    'count_sales_3': product_ids[product.id]['count_sales_3'],
                }
                product.write(vals)
            rg._cr.commit()
            self -= rg


    @api.multi
    def _compute_product_sales_bis(self):
        
        domain = [("key", "ilike", "count_sales_")]
        count = dict(
            (item["key"], int(item["value"]))
            for item in self.env["ir.config_parameter"].search_read(
                domain, ["key", "value"]
            )
        )
        domain = [("key", "=", "field_to_count")]
        field_to_count = self.env["ir.config_parameter"].search_read(
            domain, ["key", "value"]
        )
        if field_to_count:
            field_to_count = field_to_count["value"]
        else:
            field_to_count = "product_uom_qty"

        default = {"0": 0, "1": 1, "2": 2, "3": 6}
        # default = {"0": 0, "1": 3, "2": 6, "3": 9}
        date_ref = fields.Date.today()
        next_date = fields.Date.from_string(date_ref)
        res = {}
        max_month = 0
        for i in range(0, 4):
            month_str = "{}".format(i)
            month = count.get("count_sales_{}".format(i), default[month_str])
            max_month = max(max_month, month)
            start = next_date + relativedelta(day=1, months=-month)
            start_date = fields.Date.to_string(start)
            domain = ['&', '&', 
                ("state", "=", "done"),
                ("date", ">=", start_date),
                ("product_id", "in", self.ids)]
            product_ids = {}
            for product in self:
                product_ids[product.id] = 0

            domain_out = expression.AND([domain, ['&', ('location_id.usage', '!=', 'customer'), ('location_dest_id.usage', '=', 'customer')]])
            move_out = self.env["stock.move"].read_group(domain_out, ["product_id", 'product_uom_qty'], ["product_id"])
            for item in move_out:
                product_id = item['product_id'][0]
                product_ids[product_id] += item['product_uom_qty']
            #devoluciones
            domain_in = expression.AND([domain, ['&', ('location_id.usage', '=', 'customer'), ('location_dest_id.usage', '!=', 'customer')]])
            
            move_in = self.env["stock.move"].read_group(domain_in, ["product_id", 'product_uom_qty'], ["product_id"])
            for item in move_in:
                product_id = item['product_id'][0]
                product_ids[product_id] -= item['product_uom_qty']
            
            res[month_str] = product_ids
        """for i in range(0, 4):
            month_str = "{}".format(i)
            month = count.get("count_sales_{}".format(i), default[month_str])
            max_month = max(max_month, month)
            start = next_date + relativedelta(day=1, months=-month)
            start_date = fields.Date.to_string(start)
            domain = [
                ("state", "not in", ("draft", "cancel")),
                ("order_id.date_order", ">", start_date),
                ("product_id", "in", self.ids),
            ]
            res[month_str] = dict(
                (item["product_id"][0], item[field_to_count])
                for item in self.env["sale.order.line"].read_group(
                    domain, ["product_id", field_to_count], ["product_id"]
                )
            )
"""
        cont = len(self) +1
        for product in self:
        
            print ('{}: {}'.format(cont, product.name))
            cont -= 1
            for i in range(0, 4):
               
                month_str = "{}".format(i)
                if res[month_str] and res[month_str].get(product.id, False):
                    product["count_sales_{}".format(month_str)] = res[month_str][
                        product.id
                    ]
                else:
                    product["count_sales_{}".format(month_str)] = 0
                if not i:
                    month_str = "{}".format(product["count_sales_{}".format(month_str)])
                else:
                    month_str = "{}/{}".format(
                        month_str, product["count_sales_{}".format(month_str)]
                    )
                product.count_sales = month_str
            

    @api.multi
    def _compute_product_sale_alarm(self):
        next_date = fields.Date.from_string(fields.Date.today())
        for product in self:
            days = (
                product.days_for_alarm.days
                or product.product_tmpl_id.days_for_alarm.days
            )
            start = next_date + relativedelta(days=-days)
            start_date = fields.Date.to_string(start)
            domain = [
                ("state", "not in", ("draft", "cancel")),
                ("order_id.date_order", ">", start_date),
                ("product_id", "=", product.id),
            ]
            res = self.env["sale.order.line"].search_count(domain)
            product.days_with_sales = res == 0
