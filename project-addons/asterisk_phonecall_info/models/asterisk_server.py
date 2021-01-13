# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    # pip install py-Asterisk
    from Asterisk import Manager
except ImportError:
    _logger.debug('Cannot import Asterisk')
    Manager = None


class AsteriskServer(models.Model):
    _inherit = "asterisk.server"

    cdr_user = fields.Char()
    cdr_pass = fields.Char()
    cdr_file_path = fields.Char()
    cdr_last_imported_date = fields.Datetime(default=fields.Datetime.now)

    @api.model
    def _get_calling_number_from_channel(self, chan, user):
        res = super(AsteriskServer, self)._get_calling_number_from_channel(chan, user)
        internal_number = user.internal_number
        if res == False and chan.get("CallerIDNum") in internal_number:
            return chan.get("ConnectedLineNum")
        else:
            return res

    @api.model
    def _get_calling_agi_uniqueid_from_channel(self, chan, user):
        '''Method designed to be inherited to work with
        very old or very new versions of Asterisk'''
        sip_account = user.asterisk_chan_type + '/' + user.resource
        internal_number = user.internal_number

        _logger.info("_get_calling_agi_uniqueid_from_channel: SIP ACC {}, INTERNAL NUMBER: {}, CHAN: {}".format(sip_account, internal_number, chan))
        # 4 = Ring
        # 6 = Up
        if (
                chan.get('ChannelState') in ('4', '6') and (
                    chan.get('ConnectedLineNum') == internal_number or
                    chan.get('EffectiveConnectedLineNum') == internal_number or
                    sip_account in chan.get('BridgedChannel', ''))):
            _logger.info(
                "Found a matching Event with ID = %s",
                chan.get('Uniqueid'))
            return chan.get('Uniqueid')
        # Compatibility with Asterisk 1.4
        if (
                chan.get('State') == 'Up' and
                sip_account in chan.get('Link', '')):
            _logger.info("Found a matching Event in 'Up' state")
            return chan.get('Uniqueid')
        return False


    @api.model
    def _get_calling_agi_uniqueid(self, user):
        ast_manager = Manager.Manager(
                (self.ip_address, self.port),
                self.login, self.password)
        calling_party_number = False
        try:
            list_chan = ast_manager.Status()
            _logger.info("Result of Status AMI request:")
            _logger.info(format(list_chan))
            for chan in list_chan.values():
                calling_agi_uniqueid = self._get_calling_agi_uniqueid_from_channel(
                    chan, user)
                if calling_agi_uniqueid:
                    break
        except Exception as e:
            _logger.error(
                "Error in the Status request to Asterisk server %s",
                self.ip_address)
            _logger.error(
                "Here are the details of the error: '%s'", str(e))
            raise UserError(_(
                "Can't get Call unique ID  Asterisk.\nHere is the "
                "error: '%s'" % str(e)))

        finally:
            ast_manager.Logoff()

        _logger.debug("Call unique ID: '%s'", calling_agi_uniqueid)
        return calling_agi_uniqueid
