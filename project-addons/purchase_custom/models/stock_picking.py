# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
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

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delayed_mail_send = fields.Boolean(default=False)
    confirming_job_ids = fields.Many2many(comodel_name='queue.job',
                                      column1='picking_id', column2='job_id',
                                      string="Queue orders", copy=False)


    @api.multi
    def write(self, vals):
        if 'scheduled_date' in vals:
            self.change_scheduled_date_mail(vals['scheduled_date'])
            vals.update(delayed_mail_send=False)
        return super().write(vals)

    @api.model
    def get_dest_outgoing_picks(self, product_ids):
        domain = [('picking_type_id.code', '=', 'outgoing'),
                  ('product_id', 'in', product_ids.ids),
                  ('state', 'in', ['confirmed', 'partially_available'])]
        picking_ids = self.env['stock.move'].search(domain).mapped('picking_id')
        return picking_ids

    def get_notification_ids(self):
        partner_ids = self.env['res.partner']
        if self.team_id.user_id:
            partner_ids |= self.team_id.user_id.partner_id
        if self.team_id.member_ids:
            partner_ids |= self.team_id.member_ids.mapped('partner_id')
        return partner_ids


    def refresh_picking_followers(self):
        """ Actualiza seguidores de los albaranes."""
        partner_ids = self.env['res.partner']
        if self.team_id:
            partner_ids += self.team_id.user_id.partner_id
            if self.team_id.member_ids:
                partner_ids += self.team_id.member_ids.mapped('partner_id')
        follower_ids = self.sale_id.message_follower_ids + self.purchase_id.message_follower_ids
        partner_ids |= follower_ids.mapped('partner_id').filtered(lambda x: x.user_ids)
        if partner_ids:
            partner_ids = partner_ids.filtered(lambda x: x not in self.message_follower_ids.mapped('partner_id'))
            self.message_subscribe(partner_ids=partner_ids.ids)

    def write_advise_affected_picks(self, new_scheduled_date=False):
        queue_obj = self.env['queue.job']
        ctx = self._context.copy()
        for order in self:
            order2 = self.with_context(ctx,tracking_disable=True, notify_followers=False).browse(order.id)
            new_delay = order2.sudo().with_delay()._write_advise_affected_picks(new_scheduled_date)
            job = queue_obj.search([('uuid', '=', new_delay.uuid)])
            order.sudo().write({'confirming_job_ids': [(4, job.id)]})
    
    @job
    @api.multi
    def _write_advise_affected_picks(self, new_scheduled_date=False):

        """
            Actualizo los seguidores
        """
        _logger.info("Enviando mensaje de retraso del albarán %s" % self.name)
        ## self.refresh_picking_followers()
        
        if self.picking_type_code == 'incoming':
            affected_picks = self.get_dest_outgoing_picks(self.move_lines.mapped('product_id'))
        else:
            affected_picks = False
        
        _scheduled_date = fields.Datetime.to_datetime(self.scheduled_date).strftime('%d-%m-%y')
        
        if new_scheduled_date:
            _new_scheduled_date = fields.Datetime.to_datetime(new_scheduled_date).strftime('%d-%m-%y')
            body_incoming = 'La fecha de recepción del albarán <a href=#data-oe-model=stock.picking data-oe-id=%d>%s</a> ha cambiado a <strong>%s</strong>.' % (
            self.id, self.name, _new_scheduled_date)
            incoming_subject = 'Albarán %s. Cambio de fecha' % self.name
        else:            
            incoming_subject = 'Albarán %s. Retrasado/Split' % self.name
            body_incoming = 'El albarán <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> está retrasado/split. Fecha Prevista: %s' % (
                self.id, self.name, _scheduled_date)
        
        self.message_post(body=body_incoming, 
                          subject=incoming_subject, 
                          subtype='mail.mt_comment',
                          mail_server_id=2, 
                          partner_ids = self.get_notification_ids().ids)

        _logger.info("Enviando mensaje de retraso a los albaranes %s" % affected_picks.mapped('name'))

        if affected_picks:
            body_incoming += "Se pueden ver afectadas las siguientes entregas: <ul>"
            for pick in affected_picks:
                # pick.refresh_picking_followers()
                body_incoming += "<li><a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a></li>" % (pick.id, pick.name)
                # partner_ids = pick.team_id.member_ids
                # pick.message_subscribe(partner_ids=partner_ids.ids)
                if new_scheduled_date:
                    body = 'La fecha de recepción del albarán <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> ha cambiado a <strong>%s</strong>.' % (
                        self.id, self.name, _new_scheduled_date)
                    subject = 'Albarán: %s. Cambio en la fecha programada de material pendiente.' % pick.name
                else:
                    body = 'El albarán <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> está retrasado.' % (self.id, self.name)
                    subject = 'Albarán: %s. Retraso en el material pendiente.' % pick.name
                pick.message_post(body=body, 
                                  subject=subject, 
                                  subtype='mail.mt_comment', 
                                  mail_server_id=2, 
                                  partner_ids = pick.get_notification_ids().ids)
            body_incoming += "</ul>"

    @api.multi
    def change_scheduled_date_mail(self, new_scheduled_date):
        """
            Si cambiamos la fecha programada en un albarán (write de scheduled_date):
                Se envía un mail al mismo albarán con un listado de las salidas afectadas.
                Se envía un mail por cada albarán de salida afectado a los miembros del equipo de ventas.
        """
        for incoming_pick in self:
            if incoming_pick.scheduled_date != new_scheduled_date:
                incoming_pick.write_advise_affected_picks(new_scheduled_date)

    def send_advise_delayed_scheduled_email(self):

        today = fields.Datetime.today()
        # Solo se ejcuta lunes a viernes. Si no sábado y domingo repetirá los mails.
        if today.weekday() > 4:
            _logger.info("FIN DE SEMANA")
            return

        domain = [('delayed_mail_send', '=', False),
                  ('scheduled_date', '<', today),
                  ('state', 'in', ['confirmed', 'waiting', 'assigned'])]
                  
        """
            Picking_ids son los albaranes retrasados.
        """
        picking_ids = self.env['stock.picking'].search(domain)
        _logger.info("Albaranes retrasados: %s" % picking_ids.mapped('name'))
        for pick in picking_ids:
            pick.write_advise_affected_picks()
        picking_ids.write({'delayed_mail_send': True})
        return domain

    @api.multi
    def _create_backorder(self, backorder_moves=[]):
        backorder_ids = super()._create_backorder(backorder_moves=backorder_moves)
        for backorder_id in backorder_ids:
            backorder_id.message_subscribe(partner_ids=backorder_id.backorder_id.message_follower_ids.ids)
        return backorder_ids

    def pick_canceled_message(self):
        queue_obj = self.env['queue.job']
        ctx = self._context.copy()
        picks = self.with_context(ctx,tracking_disable=True, notify_followers=False).browse(self.ids)
        for order in picks:
            new_delay = order.sudo().with_delay()._pick_canceled_message()
            job = queue_obj.search([('uuid', '=', new_delay.uuid)])
            order.sudo().write({'confirming_job_ids': [(4, job.id)]})
    
    @job
    @api.multi
    def _pick_canceled_message(self):
        for pick in self:
            _logger.info ("Enviando mensajes de albarán %s cancelado"% pick.name)
            purchase_states = ['purchase', 'done', 'cancel']
            ## saco todos los productos sin replenish_type o con replenish_type == True
            product_ids = pick.filtered(lambda x: x.state == 'cancel').mapped('move_lines.product_id').filtered(lambda x: not x.replenish_type or x.replenish_type.send_cancel_mail)
            ## saco las lineas de compra asociadas a estos productos.

            ## EN PEDIDOS DE COMPRA NOT IN ['purchase', 'done', 'cancel']. Pedidos de compra no confirmados aún
            domain = [('product_id', 'in', product_ids.ids), ('order_id.state', 'not in', purchase_states)]
            line_ids = self.env['purchase.order.line'].search(domain)

            # MOVIMIENTOS DE ENTRADA NO HECHOS ASOCIADOS A PEDIDOS DE COMPRA . Pedidos de compra confirmados pero no recibidos aún
            domain = [('product_id', 'in', product_ids.ids), ('state', '=', 'assigned'), ('purchase_line_id', '!=', False)]
            line_ids |= self.env['stock.move'].search(domain).mapped('purchase_line_id')
            msg = ''
            pick_link = "<a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a>" % (pick.id, pick.name)
            for line in line_ids:
                puchase_id = line.order_id
                purchase_link = "<a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a>" % (puchase_id.id, puchase_id.name)
                product_link = "<a href=# data-oe-model=product.product data-oe-id=%d>%s</a>" % (line.product_id.id, line.product_id.display_name)
                purchase_msg = "El pedido de compra {} tiene {} unidades del artículo {} que están en el albarán cancelado {}".format(purchase_link, line.product_qty, product_link, pick_link)
                msg = '{}<hr/>{}'.format(msg, purchase_msg)
                product_id = line.product_id
                domain = [('product_id', '=', line.product_id.id), ('picking_type_id.code', '=', 'outgoing'), ('state', 'in', ['waiting', 'partially_available', 'confirmed', 'assigned'])]
                pending_moves = self.env['stock.move'].search(domain)
                if pending_moves:
                    msg = " {}<p/> Stock Actual: {} Reservado: {}. Salidas pendientes: <ul>".format(msg, product_id.qty_available, product_id.quantity_reserved)
                    for move in pending_moves:
                        pick_link = "<a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a>" % (move.picking_id.id, move.picking_id.display_name)
                        m1 = "<li>Albarán {}.Pedido: {} Reservado: {}.</li>".format(pick_link, move.product_uom_qty, move.reserved_availability)
                        msg = '{}{}'.format(msg, m1)
                    msg = '{}</ul>'.format(msg)
                puchase_id.message_post(body = msg, 
                                        subject = 'Albarán {} cancelado'.format(pick.name),     
                                        subtype='mail.mt_comment', 
                                        mail_server_id=2,
                                        partner_ids = puchase_id.get_notification_ids().ids)
            pick.message_post(body = msg, 
                              subject = 'Albarán {} cancelado'.format(pick.name), 
                              subtype='mail.mt_comment', 
                              mail_server_id=2,
                              partner_ids = pick.get_notification_ids().ids)



    @api.multi
    def action_cancel(self):
        outgoing_picks = self.filtered(lambda x: x.picking_type_id.code == 'outgoing' and x.state not in ('cancel', 'draft'))
        res = super().action_cancel()
        ## Si un albarán que tiene artículos marcados como replenish_type.send_cancel_mail se cancela
        # Se busca si tiene compras asociadas: Sin confirmar o ya confirmadas y no recibidas
        # Y se envía un mensaje a los seguidores de los pedidos de compra.
        outgoing_picks.filtered(lambda x: x.state == 'cancel').pick_canceled_message()
        return res
        """
        for pick in outgoing_picks.filtered(lambda x: x.state == 'cancel'):
            purchase_states = ['purchase', 'done', 'cancel']
            ## saco todos los productos sin replenish_type o con replenish_type == True
            product_ids = pick.filtered(lambda x: x.state == 'cancel').mapped('move_lines.product_id').filtered(lambda x: not x.replenish_type or x.replenish_type.send_cancel_mail)
            ## saco las lineas de compra asociadas a estos productos.

            ## EN PEDIDOS DE COMPRA NOT IN ['purchase', 'done', 'cancel']. Pedidos de compra no confirmados aún
            domain = [('product_id', 'in', product_ids.ids), ('order_id.state', 'not in', purchase_states)]
            line_ids = self.env['purchase.order.line'].search(domain)

            # MOVIMIENTOS DE ENTRADA NO HECHOS ASOCIADOS A PEDIDOS DE COMPRA . Pedidos de compra confirmados pero no recibidos aún
            domain = [('product_id', 'in', product_ids.ids), ('state', '=', 'assigned'), ('purchase_line_id', '!=', False)]
            line_ids |= self.env['stock.move'].search(domain).mapped('purchase_line_id')
            msg = ''
            pick_link = "<a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a>" % (pick.id, pick.name)
            for line in line_ids:
                puchase_id = line.order_id
                purchase_link = "<a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a>" % (puchase_id.id, puchase_id.name)
                product_link = "<a href=# data-oe-model=product.product data-oe-id=%d>%s</a>" % (line.product_id.id, line.product_id.display_name)
                purchase_msg = "El pedido de compra {} tiene {} unidades del artículo {} que están en el albarán cancelado {}".format(purchase_link, line.product_qty, product_link, pick_link)
                msg = '{}<hr/>{}'.format(msg, purchase_msg)
                product_id = line.product_id
                domain = [('product_id', '=', line.product_id.id), ('picking_type_id.code', '=', 'outgoing'), ('state', 'in', ['waiting', 'partially_available', 'confirmed', 'assigned'])]
                pending_moves = self.env['stock.move'].search(domain)
                if pending_moves:
                    msg = " {}<p/> Stock Actual: (Reservada) {} ({}) Unidades. Salidas pendientes: <ul>".format(msg, product_id.qty_available, product_id.quantity_reserved)
                    for move in pending_moves:
                        pick_link = "<a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a>" % (move.picking_id.id, move.picking_id.display_name)
                        m1 = "<li>Albarán {}. {} Reservado: {} Unidades</li>".format(pick_link, move.product_uom_qty, move.reserved_availability)
                        msg = '{}{}'.format(msg, m1)
                    msg = '{}</ul>'.format(msg)
                puchase_id.message_post(body = msg, subject = 'Albarán {} cancelado'.format(pick.name), subtype='mail.mt_comment', mail_server_id=2)
            
            pick.message_post(body = msg, subject = 'Albarán {} cancelado'.format(pick.name), subtype='mail.mt_comment', mail_server_id=2)
        return res
        """

    @api.multi
    def split_process(self):
        super().split_process()
        for pick in self:
            pick.backorder_id.write_advise_affected_picks()