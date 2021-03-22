# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from datetime import datetime, timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        res = super().action_confirm()
        for sale in self:
            ## Si se confirma una venta se añaden como seguidores los miembros del equipo de ventas y el líder del equipo
            partner_ids = self.env['res.partner']
            partner_ids += sale.team_id.user_id.partner_id
            if sale.team_id.member_ids:
                partner_ids += self.team_id.member_ids.mapped('partner_id')
            if partner_ids:
                partner_ids = partner_ids.filtered(
                    lambda x: x not in sale.message_follower_ids.mapped('partner_id'))
                sale.message_subscribe(partner_ids=partner_ids.ids)

            mail_line = ''
            for line in sale.order_line.mapped('move_ids'):
                product = line.product_id
                if line.product_uom_qty > product.qty_available:
                    delay = product.variant_seller_ids and product.variant_seller_ids[0].delay or 1
                    if delay > 1:
                        seller = product.variant_seller_ids[0]
                        ispack = '' if line.sale_line_id.product_id == product else ' (Pack)'
                        # Cantidad pedida > que existencias NO reservadas y delay del primer proveedor > 1 día
                        mail_line += "<li>El proveedor %s tiene un tiempo de entrega de %s día(s) para el artículo %s%s</li>"%(
                          seller.name.display_name, seller.delay, product.display_name, ispack
                        )
            if mail_line:
                body = 'El pedido tiene los siguientes artículos sin stock con tiempo de entrega superior a 24 horas<ul>%s</ul>'%mail_line
                subject = 'Pedido %s. No stock en 24 Horas'%sale.name
                sale.message_post(body=body, subject=subject, subtype='mail.mt_comment', mail_server_id=2, email_to=sale.team_id.team_email)
        return res






