# -*- coding: utf-8 -*-
# Copyright 2014-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
from odoo.addons.web.controllers.main import clean_action
import logging

logger = logging.getLogger(__name__)


class PhoneCommon(models.AbstractModel):
    _inherit = 'phone.common'

    @api.model
    def incall_notify_by_login(self, number, login_list):
        assert isinstance(login_list, list), 'login_list must be a list'
        res = self.get_record_from_phone_number(number)
        users = self.env['res.users'].search(
            [('login', 'in', login_list)])
        logger.info(
            'Notify incoming call from number %s to user IDs %s'
            % (number, users.ids))
        action = self._prepare_incall_pop_action(res, number)
        action = clean_action(action)
        if action:
            for user in users:
                channel = 'notify_info_%s' % user.id
                bus_message = {
                    'message': _('Incoming call from {}'.format(number)),
                    'title': _('Incoming call'),
                    'action': action,
                    'sticky': True,
                    'action_link_name': 'action_link_name',
                }

                self.sudo().env['bus.bus'].sendone(
                    channel, bus_message)
                logger.debug(
                    'This action has been sent to user ID %d: %s'
                    % (user.id, action))
        if res:
            callerid = res[2]
        else:
            callerid = False
        
        # Save phonecall info

        return callerid