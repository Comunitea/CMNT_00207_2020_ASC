# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta

class ProductAlarmDays(models.Model):
    _name = "product.alarm.days"

    code = fields.Char('Code')
    days = fields.Integer('# Days')

    @api.multi
    def name_get(self):
        res = []
        for alarm in self:
            name = '{}: {} days'.format(alarm.code, alarm.days)
            res.append((alarm.id, name))
        return res

class ProductTemplate(models.Model):
    _inherit = "product.template"

    count_sales = fields.Char('Count sales')
    count_sales_0 = fields.Monetary(compute='_compute_product_sales', string="Count sales 0")
    count_sales_1 = fields.Monetary(compute='_compute_product_sales', string="Count sales 1")
    count_sales_2 = fields.Monetary(compute='_compute_product_sales', string="Count sales 2")
    count_sales_3 = fields.Monetary(compute='_compute_product_sales', string="Count sales 3")
    days_with_sales = fields.Boolean(string="Sale alarm day")
    days_for_alarm = fields.Many2one('product.alarm.days', string="Days for sale alarm")

    @api.multi
    def _compute_product_sales(self):
        domain = [('key', 'ilike', 'count_sales_')]
        count = dict((item['key'], item['value']) for item in self.env['ir.config_parameter'].search_read(domain, ['key', 'value']))
        default = {'0': 0, '1': 1, '2':2, '3': 6}
        date_ref = fields.Date.today()
        next_date = fields.Date.from_string(date_ref)
        res = {}
        for i in range(0,4):
            str = '{}'.format(i)
            month = count.get('count_sales_{}'.format(i), default[str])
            start = next_date + relativedelta(day=1, months=-month)
            start_date = fields.Date.to_string(start)
            domain = [('state', 'not in', ('draft', 'cancel')), ('order_id.date_order', '>', start_date), ('product_id', 'in', self.ids)]
            res[str] = dict((item['product_id'][0], item['price_subtotal']) for item in
                   self.env['sale.order.line'].read_group(domain, ['product_id', 'price_subtotal'], ['product_id'], orderby='id'))

        for product in self:
            for i in range(0, 4):
                str = '{}'.format(i)
                if res[str] and res[str][product.id]:
                    product['count_sales_{}'.format(str)] = res[str][product.id]
                else:
                    product['count_sales_{}'.format(str)] = 0
                if not i:
                    str= '{}'.format(product['count_sales_{}'.format(str)])
                else:
                    str = '{}/{}'.format(str, product['count_sales_{}'.format(str)])
                product.count_sales = str
    @api.multi
    def compute_product_sale_alarm(self):
        import pdb; pdb.set_trace()
        next_date = fields.Date.from_string(fields.Date.today())
        for product in self:
            days = product.days_for_alarm.days
            start = next_date + relativedelta(days=-days)
            start_date = fields.Date.to_string(start)
            domain = [('state', 'not in', ('draft', 'cancel')), ('order_id.date_order', '>', start_date), ('product_id', '=', product.id)]
            res = self.env['sale.order.line'].search_count(domain)
            product.days_with_sales = res > 0



