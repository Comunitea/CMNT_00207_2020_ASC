# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.queue_job.job import job
except ImportError:
    _logger.debug('Can not `import queue_job`.')
    import functools

    def empty_decorator_factory(*argv, **kwargs):
        return functools.partial
    job = empty_decorator_factory


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_line_common = fields.Float(
        string='Descuento Líneas(%)', digits=dp.get_precision('Discount'),
    )
    confirming_job_ids = fields.Many2many(comodel_name='queue.job',
                                      column1='order_id', column2='job_id',
                                      string="Queue orders", copy=False)
    def apply_purchase_line_common(self):
        for line in self.order_line:
            line.discount = self.purchase_line_common

    def add_purchase_default_follower(self):
        ids = self.env['ir.config_parameter'].sudo().get_param('purchase_custom.auto_add_follower')
        partner_ids = self.env['res.partner']
        if ids:
            partner_ids = self.env['res.partner'].browse(eval(ids))
        ## añado como seguidor a quien confirme el pedido de compra
        ## y el/ los id de los usuarios que estén en purchase_custom.auto_add_follower
        for purchase in self:
            partner_ids |= purchase.env.user and purchase.env.user.partner_id or self.env['res.partner']
            if partner_ids:## and partner_id not in self.message_follower_ids.mapped('partner_id'):
                self.message_subscribe(partner_ids=partner_ids.ids)
        return True

    @api.model
    def create(self, vals):
        purchase = super().create(vals)
        if purchase.state == 'purchase':
            purchase.add_purchase_default_follower()
        return purchase

    @api.multi
    def write(self, vals):
        if 'state' in vals and vals['state'] == 'purchase':
            self.add_purchase_default_follower()
        return super().write(vals)


    @api.multi
    def send_mail_to_waiting_picks(self):
        ## Al confirmar una compra, se enviará un correo a los pedidos de venta
        ## que tengan material en espera de esta compra.
        
        states = ['confirmed', 'waiting', 'partially_available']
        product_ids = self.mapped('order_line.product_id')
        move_domain = [('picking_type_id.code', '=', 'outgoing'), ('product_id', 'in', product_ids.ids), ('state', 'in', states)]
        move_ids = self.env['stock.move'].search(move_domain)
        
        for po in self:            
            msg = {}
            po_product_ids = po.order_line.mapped('product_id')
            po_move_ids = move_ids.filtered(lambda x: x.product_id in po_product_ids)
            if not po_move_ids:
                continue
            
            po_link =  "<a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a>" % (po.id, po.name)
            for move_id in po_move_ids:
                picking_id = move_id.picking_id
                product_id_link = "<a href=# data-oe-model=product.product data-oe-id=%d>%s</a>" % (move_id.product_id.id, move_id.product_id.display_name)
                if not picking_id in msg: msg.update({picking_id: ''})
                po_lines = po.order_line.filtered(lambda x: x.product_id == move_id.product_id)
                for po_line in po_lines:
                    msg[picking_id] = '{}<li> El artículo {} está en el {}. Fecha prevista {}. Cantidad. {}</li>'.format(msg[picking_id], product_id_link, po_link, po_line.date_planned, po_line.product_qty)
            
            po_body = 'Lista de salidas en espera:<ul>'
            for outgoing_pick in msg:
                outgoing_pick_link = "<a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a>" % (outgoing_pick.id, outgoing_pick.name)
                subject = "Previsión de recepciones del albarán {}".format(outgoing_pick.name)
                body ="Previsión de recepciones <ul>{}</ul>".format(msg[outgoing_pick])
                po_body = '%s<li>%s</li>'%(po_body, outgoing_pick_link)
                outgoing_pick.sale_id.message_post(body=body, subject=subject, subtype='mail.mt_comment', mail_server_id=2, email_to=outgoing_pick.team_id.team_email)
                print (outgoing_pick.name)
            po_body = "%s</ul>"%po_body    
            po.message_post(body=po_body)

    @job
    @api.multi
    def job_send_mail_to_waiting_picks(self):
        self.ensure_one()
        ctx = self._context.copy()
        ctx.update({'do_super': True})
        self.with_context(ctx).send_mail_to_waiting_picks()
        

    @api.multi
    def button_confirm(self):
        super().button_confirm()
        queue_obj = self.env['queue.job']
        ctx = self._context.copy()
        for order in self:
            notif_user = order.env.user.id
            order2 = self.with_context(ctx,tracking_disable=True).browse(order.id)
            new_delay = order2.sudo().with_delay().job_send_mail_to_waiting_picks()
            job = queue_obj.search([('uuid', '=', new_delay.uuid)])
            order.sudo().write({'confirming_job_ids': [(4, job.id)]})
            # self.send_mail_to_waiting_picks()
        return True