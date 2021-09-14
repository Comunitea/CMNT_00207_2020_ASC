# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from datetime import date


class RmaOrder(models.Model):

    _name = 'rma.order'
    _inherit = ['rma.order', 'portal.mixin']

    order_id = fields.Many2one('sale.order')
    pickup_time = fields.Datetime()
    operation_type = fields.Selection([('return', 'Return'), ('rma', 'RMA')])
    return_from_sale = fields.Many2one('sale.order')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.partner_id not in res.message_partner_ids:
            res.message_subscribe([res.partner_id.id])
        return res

    @api.model
    def check_sale_dates(self, order_reference):
        order_exists = self.env['sale.order'].search([('name', '=ilike', order_reference)])
        if order_exists:
            return (date.today() - order_exists.date_order.date()).days
        return -1

    def _compute_access_url(self):
        super(RmaOrder, self)._compute_access_url()
        for rma in self:
            rma.access_url = '/my/rma/%s' % (rma.id)


class RmaOrderLine(models.Model):
    _inherit = 'rma.order.line'

    product_ref = fields.Char()
