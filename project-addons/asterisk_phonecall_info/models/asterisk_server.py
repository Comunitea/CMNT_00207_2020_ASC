# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import logging
_logger = logging.getLogger(__name__)

try:
    # pip install py-Asterisk
    from Asterisk import Manager
except ImportError:
    _logger.debug('Cannot import Asterisk')
    Manager = None


class AsteriskServer(models.Model):
    '''Asterisk server object, stores the parameters of the Asterisk IPBXs'''
    _inherit = "asterisk.server"

    @api.model
    def get_record_from_my_channel(self):
        res = super(AsteriskServer, self).get_record_from_my_channel()
        if res and res[1]:
            partner_id = self.env['res.partner'].browse(res[1])
            user, ast_server, ast_manager = self._connect_to_asterisk()

            try:
                list_chan = ast_manager.Status()
                for chan in list_chan.values():
                    #{'Privilege': 'Call', 'ChannelState': '6', 'ChannelStateDesc': 'Up', 'CallerIDNum': '101', 
                    #'CallerIDName': '<unknown>', 'ConnectedLineNum': '102', 'ConnectedLineName': '<unknown>', 'Accountcode': '', 
                    #'Context': 'internal', 'Exten': '', 'Priority': '1', 'Uniqueid': '1590420999.92', 'Linkedid': '1590420999.90', 
                    #'Type': 'SIP', 'DNID': '', 'EffectiveConnectedLineNum': '102', 'EffectiveConnectedLineName': '<unknown>', 
                    #'TimeToHangup': '0', 'BridgeID': '57d4d931-fee5-438d-bf59-5c925c7cee9e', 'Application': 'AppDial', 
                    #'Data': '(Outgoing Line)', 'Nativeformats': '(alaw)', 'Readformat': 'alaw', 'Readtrans': '', 
                    #'Writeformat': 'alaw', 'Writetrans': '', 'Callgroup': '0', 'Pickupgroup': '0', 'Seconds': '851'}
                    internal_number = user.internal_number
                    if(chan.get('ChannelState') in ('4', '6') and (
                        chan.get('ConnectedLineNum') == internal_number or
                        chan.get('EffectiveConnectedLineNum') == internal_number)):
                        crm_phonecall = self.env['crm.phonecall'].search([
                            ('asterisk_id', '=', chan.get('Linkedid'))
                        ])
                        try:
                            if crm_phonecall:
                                crm_phonecall.update({
                                    'length': chan.get('Seconds'),
                                })
                            else:
                                crm_phonecall = self.env['crm.phonecall'].create({
                                    'state': 'open',
                                    'partner_id': partner_id.id,
                                    #'tag_ids': [],
                                    'user_id': user.id,
                                    'name': 'Llamada centralita',
                                    'asterisk_id': chan.get('Linkedid'),
                                    'length': chan.get('Seconds'),
                                    'extension': chan.get('Data'),
                                })
                        
                        except Exception as e:
                            _logger.error(
                                "Error creating crm.phonecall: '%s'", str(e))
                            raise UserError(_(
                                "Error creating crm.phonecall.\nHere is the "
                                "error: '%s'" % str(e)))
                    
            except Exception as e:
                _logger.error(
                    "Error in the Status request to Asterisk server %s",
                    ast_server.ip_address)
                _logger.error(
                    "Here are the details of the error: '%s'", str(e))
                raise UserError(_(
                    "Can't get calling number from  Asterisk.\nHere is the "
                    "error: '%s'" % str(e)))

            finally:
                ast_manager.Logoff()
        return res