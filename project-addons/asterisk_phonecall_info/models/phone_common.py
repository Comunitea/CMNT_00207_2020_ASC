# Copyright 2014-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
from odoo.addons.web.controllers.main import clean_action
import logging
from odoo.exceptions import UserError

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
        partner_id = self.env['phone.common'].get_record_from_phone_number(number)
        if partner_id and partner_id[2]:
            partner_name = partner_id[2]
        else:
            partner_name = 'Unknown'
        if action:
            for user in users:
                channel = 'notify_info_%s' % user.id
                bus_message = {
                    'message': _('Incoming call from {} ({})'.format(partner_name, number)),
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

        return callerid

    @api.model
    def save_phonecall_record(self, data, number):
        
        ## Agi data
        ##{'agi_type': 'SIP', 'agi_channel': 'SIP/101-00000065', 'agi_threadid': '139807535195904',
        ## 'agi_priority': '1', 'agi_dnid': '102', 'agi_extension': '102', 'agi_rdnis': 'unknown',
        ##  'agi_context': 'internal', 'agi_callerid': '101', 'agi_uniqueid': '1590598791.737', 
        ##  'agi_version': '13.30.0', 'agi_request': '/usr/local/bin/set_name_incoming_timeout.sh', 
        ##  'agi_callington': '0', 'agi_language': 'en', 'agi_callingtns': '0', 'agi_accountcode': '', 
        ##  'agi_calleridname': 'vicen', 'agi_enhanced': '0.0', 'agi_callingpres': '0', 'agi_callingani2': '0'}

        logger.info('Saving call from number {} with data {}'.format(number, data))

        partner_id = self.env['phone.common'].get_record_from_phone_number(number)
        
        #user_id = self.env['phone.common'].get_record_from_phone_number(data.get('agi_dnid'))

        if partner_id and partner_id[1]:
            logger.info('Localiced partner: {}'.format(partner_id))
            crm_phonecall = self.env['crm.phonecall'].search([
                ('asterisk_id', '=', data.get('agi_uniqueid'))
            ])            
            try:
                if crm_phonecall:
                    #crm_phonecall.update({
                    #    'length': data.get('Seconds'),
                    #})
                    logger.info(
                        'Updated call {}'.format(crm_phonecall.id))
                else:
                    crm_phonecall = self.env['crm.phonecall'].create({
                        'state': 'open',
                        'partner_id': partner_id[1],
                        #'tag_ids': [],
                        #'user_id': user_id[1],
                        'name': 'Llamada centralita',
                        'asterisk_id': data.get('agi_uniqueid'),
                        #'length': data.get('Seconds'),
                        'extension': data.get('agi_extension'),
                    })
                    logger.info(
                        'Created call {}'.format(crm_phonecall.id))
            
            except Exception as e:
                logger.error(
                    "Error creating crm.phonecall: '%s'", str(e))
                raise UserError(_(
                    "Error creating crm.phonecall.\nHere is the "
                    "error: '%s'" % str(e)))
        return True