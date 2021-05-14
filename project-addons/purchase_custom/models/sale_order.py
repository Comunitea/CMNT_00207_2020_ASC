# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from datetime import datetime, timedelta


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

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    confirming_job_ids = fields.Many2many(comodel_name='queue.job',
                                      column1='order_id', column2='job_id',
                                      string="Queue orders", copy=False)


    def get_notification_ids(self):
        partner_ids = self.user_id.partner_id
        if self.team_id.user_id:
            partner_ids |= self.team_id.user_id.partner_id
        if self.team_id.member_ids:
            partner_ids |= self.team_id.member_ids.mapped('partner_id')
        return partner_ids

    @api.multi
    def add_team_followers(self):
        for sale in self:
            partner_ids = self.env['res.partner']
            partner_ids += sale.team_id.user_id.partner_id
            if sale.team_id.member_ids:
                partner_ids += self.team_id.member_ids.mapped('partner_id')
            partner_ids = partner_ids.filtered(
                lambda x: x not in sale.message_follower_ids.mapped('partner_id'))
            if partner_ids:
                sale.message_subscribe(partner_ids=partner_ids.ids)
    
    @api.multi
    def send_mail_no_stock(self):
        _logger.info("ENtrando en send_mail_no_stock")
        ctx = self._context.copy()
        ctx.update(notify_followers=False)
        for sale in self:
            mail_line = ''
            for move in sale.order_line.mapped('move_ids').filtered(lambda x: x.state not in ['cancel', 'done', 'draft']):
                product = move.product_id
                if move.product_uom_qty > product.qty_available:
                    ispack = '' if move.sale_line_id.product_id == product else ' (Componente de %s)'%move.sale_line_id.product_id.default_code
                    seller =  product.variant_seller_ids and product.variant_seller_ids[0]
                    if seller and seller.delay > 1:
                        # Cantidad pedida > que existencias NO reservadas y delay del primer proveedor > 1 día
                        
                        # mail_line += "<li>El artículo %s%s no tiene stock suficiente. El proveedor %s tiene un tiempo de entrega de %s día(s)</li>"%(
                        #  product.display_name, ispack, seller.name.display_name, seller.delay
                        #)

                        mail_line += "<li>El artículo %s%s no tiene stock suficiente. El proveedor tiene un tiempo de entrega mayor de 1 día."%(
                          product.display_name, ispack
                        )
                    else:
                        # No tiene vendedor o retraso un día.
                        mail_line += "<li>El artículo %s%s no tiene stock suficiente"%(
                          product.display_name, ispack
                        )
                    ### 
                    domain = [('picking_type_id.code', '=', 'incoming'), 
                              ('purchase_line_id', '!=', False), 
                              ('product_id', '=', product.id),
                              ('state', '=', 'assigned')]
                    sm = self.env['stock.move'].search(domain, limit=1, order="date asc")
                    if sm:
                        date = fields.Datetime.to_datetime(sm.date).strftime('%d-%m-%y')
                        mail_line += ". Previsto el {}</li>".format(date)
                    else:
                        mail_line += ". Sin fecha de llegada.</li>"


            if mail_line:
                body = 'El pedido tiene los siguientes artículos sin stock suficiente<ul>%s</ul>'%mail_line
                subject = 'Pedido %s. Artículos sin stock'%sale.name
                sale.with_context(ctx).message_post(
                    body=body, 
                    subject=subject, 
                    subtype='mail.mt_comment', 
                    mail_server_id=2, 
                    partner_ids = sale.get_notification_ids().ids
                )
    

    @job
    @api.multi
    def job_send_mail_no_stock(self):
        _logger.info("ENtrando en job_send_mail_no_stock")
        self.ensure_one()
        # self.add_team_followers()
        self.send_mail_no_stock()
       
    @api.multi
    def action_confirm(self):
        res = super().action_confirm()
        queue_obj = self.env['queue.job']
        ctx = self._context.copy()
        for order in self:
            notif_user = order.env.user.id
            order2 = self.with_context(ctx,tracking_disable=True, notify_followers=False).browse(order.id)
            new_delay = order2.sudo().with_delay().job_send_mail_no_stock()
            job = queue_obj.search([('uuid', '=', new_delay.uuid)])
            order.sudo().write({'confirming_job_ids': [(4, job.id)]})
            # self.send_mail_to_waiting_picks()
        """
        for order in self:
            ctx = self._context.copy()
            ctx.update(notify_followers=False)
            order.with_context(ctx).send_mail_no_stock()
        """
        return res
       





