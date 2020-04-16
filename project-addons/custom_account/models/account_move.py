# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):

    _name = "account.move"
    _inherit = ["account.move", "mail.thread", "mail.activity.mixin"]
