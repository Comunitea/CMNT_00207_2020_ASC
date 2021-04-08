# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delayed_mail_send = fields.Boolean(default=False)

    @api.multi
    def write(self, vals):
        if 'scheduled_date' in vals:
            self.change_scheduled_date_mail(vals['scheduled_date'])
            vals.update(delayed_mail_send=False)
        return super().write(vals)

    @api.model
    def get_dest_outgoing_picks(self):

        product_ids = self.move_lines.mapped('product_id')
        domain = [('picking_id.ready_to_send', '=', True),
                  ('product_id', 'in', product_ids.ids),
                  ('state', 'in', ['confirmed', 'partially_available'])]
        picking_ids = self.env['stock.move'].search(domain).mapped('picking_id')
        return picking_ids

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
        """
            Actualizo los seguidores
        """
        _logger.info("Enviando mensaje de retraso del albarán %s" % self.name)
        self.refresh_picking_followers()
        if self.picking_type_code == 'incoming':
            affected_picks = self.get_dest_outgoing_picks()
        else:
            affected_picks = False

        if new_scheduled_date:
            body_incoming = 'La fecha de recepción del albarán <a href=#data-oe-model=stock.picking data-oe-id=%d>%s</a> ha cambiado de %s a <strong>%s</strong>.' % (
            self.id, self.name, self.scheduled_date, new_scheduled_date)
            incoming_subject = 'Albarán %s. Cambio de fecha' % self.name
        else:
            incoming_subject = 'Albarán %s. Retrasado' % self.name
            body_incoming = 'El albarán <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> está retrasado. Fecha Prevista: %s' % (self.id, self.name, self.scheduled_date)

        if affected_picks:
            body_incoming += "Se pueden ver afectadas las siguientes entregas: <ul>"
            for pick in affected_picks:
                pick.refresh_picking_followers()
                body_incoming += "<li><a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a></li>" % (pick.id, pick.name)
                partner_ids = pick.team_id.member_ids
                pick.message_subscribe(partner_ids=partner_ids.ids)
                if new_scheduled_date:
                    body = 'La fecha de recepción del albarán <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> ha cambiado de %s a <strong>%s</strong>.' % (self.id, self.name, self.scheduled_date, new_scheduled_date)
                    subject = 'Albarán: %s. Cambio en la fecha programada de material pendiente.' % pick.name
                else:
                    body = 'El albarán <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> está retrasado.' % (self.id, self.name)
                    subject = 'Albarán: %s. Retraso en el material pendiente.' % pick.name
                pick.message_post(body=body, subject=subject, subtype='mail.mt_comment', mail_server_id=2, email_to=pick.team_id.team_email)
            body_incoming += "</ul>"
        self.message_post(body=body_incoming, subject=incoming_subject, subtype='mail.mt_comment',
                                       mail_server_id=2, email_cc=self.team_id and self.team_id.team_email or '')

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
                  ('state', '=', 'assigned')]
        """
            Picking_ids son los albaranes retrasados.
        """
        picking_ids = self.env['stock.picking'].search(domain)
        _logger.info("Alabranes retrasados: %s" % picking_ids.mapped('name'))
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

