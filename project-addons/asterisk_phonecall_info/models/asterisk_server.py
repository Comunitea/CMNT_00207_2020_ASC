# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AsteriskServer(models.Model):
    _inherit = "asterisk.server"

    @api.model
    def _get_calling_number_from_channel(self, chan, user):
        res = super(AsteriskServer, self)._get_calling_number_from_channel(chan, user)
        internal_number = user.internal_number
        if (res == False and chan.get('CallerIDNum') == internal_number):
            return chan.get('ConnectedLineNum')
        else:
            return res