# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_risk_allow_edit(self):
        self.update({'risk_allow_edit': self.env.user.has_group(
            'account_payment_order.group_account_payment')})
