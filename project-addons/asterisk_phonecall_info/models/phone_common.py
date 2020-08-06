# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
from odoo.addons.web.controllers.main import clean_action
import logging
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class PhoneCommon(models.AbstractModel):
    _inherit = "phone.common"

    @api.model
    def incall_notify_by_login(self, number, login_list):
        assert isinstance(login_list, list), "login_list must be a list"
        res = self.get_record_from_phone_number(number)
        users = self.env["res.users"].search([("login", "in", login_list)])
        logger.info(
            "Notify incoming call from number %s to user IDs %s" % (number, users.ids)
        )
        action = self._prepare_incall_pop_action(res, number)
        action = clean_action(action)
        partner_id = self.env["phone.common"].get_record_from_phone_number(number)
        if partner_id and partner_id[2]:
            partner_name = partner_id[2]
        else:
            partner_name = "Unknown"
        if action:
            for user in users:
                channel = "notify_info_%s" % user.id
                bus_message = {
                    "message": _(
                        "Incoming call from {} ({})".format(partner_name, number)
                    ),
                    "title": _("Incoming call"),
                    "action": action,
                    "sticky": True,
                    "action_link_name": "action_link_name",
                }

                self.sudo().env["bus.bus"].sendone(channel, bus_message)
                logger.debug(
                    "This action has been sent to user ID %d: %s" % (user.id, action)
                )
        if res:
            callerid = res[2]
        else:
            callerid = False

        return callerid