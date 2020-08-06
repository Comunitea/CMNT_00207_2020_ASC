# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, _
import logging
from odoo.exceptions import UserError
logger = logging.getLogger(__name__)

class PickingSignWizard(models.TransientModel):

    _name = 'phonecall.notes.wizard'

    notes = fields.Char()

    def confirm(self):
        if not self.env.context.get('default_calling_number'):
            return False
        
        default_calling_number = self.env.context.get('default_calling_number')

        if not default_calling_number[0] or not default_calling_number[1]:
            return False

        object_id = self.env[default_calling_number[0]].browse(default_calling_number[1])
        partner_id = None
        opportunity_id = None

        if default_calling_number[0] == 'crm.lead':
            opportunity_id = object_id
            if opportunity_id.partner_id:
                partner_id = opportunity_id.partner_id
        elif default_calling_number[0] == 'res.partner':
            partner_id = object_id

        user = self.env.user
        # server
        ast_server = user.get_asterisk_server_from_user()
        agi_unique_id = ast_server._get_calling_agi_uniqueid(user)

        if not agi_unique_id:
            logger.info("There is no agi_unique_id")
            return False

        crm_phonecall = self.env["crm.phonecall"].search(
            [("asterisk_id", "=", agi_unique_id)]
        )
        try:
            if crm_phonecall:
                crm_phonecall.update({
                    'notes': self.notes,
                })
                logger.info("Updated call {}".format(crm_phonecall.id))
            else:
                crm_phonecall = self.env["crm.phonecall"].create(
                    {
                        "state": "done",
                        "partner_id": partner_id.id if partner_id else None,
                        "opportunity_id": opportunity_id.id if opportunity_id else None,
                        "name": _("Call from the switchboard"),
                        "asterisk_id": agi_unique_id,
                        "extension": user.resource,
                        'user_id': user.id,
                        'notes': self.notes,
                    }
                )
                logger.info("Created call {}".format(crm_phonecall.id))

        except Exception as e:
            logger.error("Error creating crm.phonecall: '%s'", str(e))
            raise UserError(
                _(
                    "Error creating crm.phonecall.\nHere is the "
                    "error: '%s'" % str(e)
                )
            )