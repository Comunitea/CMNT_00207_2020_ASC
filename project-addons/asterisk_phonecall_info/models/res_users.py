# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _, fields
import logging
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    asterisk_notify = fields.Boolean(string='Asterisk notify', default=True)
    asterisk_user_type = fields.Selection(
        [('commercial', 'Commercial'),
         ('technical', 'Technical'),
         ('undefined', 'Undefined')],
        string='User type',
        required=True,
        default='undefined',
    )