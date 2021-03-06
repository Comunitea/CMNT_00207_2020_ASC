# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from odoo.osv import expression

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

    count_sales = fields.Char("Count sales")
    count_sales_0 = fields.Float(string="Count sales 0")
    count_sales_1 = fields.Float(string="Count sales 1")
    count_sales_2 = fields.Float(string="Count sales 2")
    count_sales_3 = fields.Float(string="Count sales 3")
    days_with_sales = fields.Boolean(string="Sale alarm day")
    days_for_alarm = fields.Many2one("product.alarm.days", string="Days for sale alarm")

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

    count_sales = fields.Char("Count sales")
    count_sales_0 = fields.Float(string="Count sales 0")
    count_sales_1 = fields.Float(string="Count sales 1")
    count_sales_2 = fields.Float(string="Count sales 2")
    count_sales_3 = fields.Float(string="Count sales 3")
    days_with_sales = fields.Boolean(string="Sale alarm day")
    days_for_alarm = fields.Many2one("product.alarm.days", string="Days for sale alarm")

    @api.multi
    def compute_product_sales(self):
        if not self:
            self = self.search([])
        self._compute_product_sales()

    @api.multi
    def _compute_product_sales(self):
         
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
