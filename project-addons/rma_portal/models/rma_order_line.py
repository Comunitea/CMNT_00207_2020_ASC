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
    creation_date = fields.Date(compute='_compute_creation_date', store=True)
    reception_date = fields.Date()
    finish_date = fields.Date()
    mail_sended = fields.Boolean()
    stage_id = fields.Many2one('rma.order.stage', domain=[('type', '=', 'order')])

    @api.depends('create_date')
    def _compute_creation_date(self):
        for r in self:
            r.creation_date = r.create_date.date()

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

    def send_mail(self):
        self.ensure_one()

        template = self.env.ref(
            "rma_portal.email_template_rma", False
        )
        ctx = dict(self._context)
        ctx.update(url=self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
        ctx.update(
            {
                    "default_model": "rma.order",
                    "default_res_id": self.id,
                    "default_use_template": bool(template.id),
                    "default_template_id": template.id,
                    "default_composition_mode": "comment",
                }
            )

        composer_id = self.env["mail.compose.message"].sudo().with_context(ctx).create({})
        values = composer_id.onchange_template_id(
            template.id, "comment", 'rma.order', self.id
        )["value"]
        composer_id.write(values)
        if self.delivery_tag:
            tag_attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'rma.order'),
                ('res_field', '=', 'delivery_tag'),
                ('res_id', '=', self.id),
            ], limit=1)
            composer_id.attachment_ids += tag_attachment
        composer_id.with_context(ctx).send_mail()


class RmaOrderLine(models.Model):
    _inherit = 'rma.order.line'

    product_ref = fields.Char()
    invoice_ref = fields.Char()
    invoice_id = fields.Many2one('account.invoice')
    stage_id = fields.Many2one('rma.order.stage', domain=[('type', '=', 'line')])


class RmaOrderStage(models.Model):
    _name = 'rma.order.stage'

    name = fields.Char(required=True)
    type = fields.Selection([('line', 'Line'), ('order', 'Order')], required=True)
    sequence = fields.Integer()
