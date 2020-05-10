# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    def compute_deposit_domain(self):
        return [
            ("order_partner_id", "child_of", [self.id]),
            ("deposit", "=", True),
        ]

    @api.multi
    def _compute_deposit_ids(self):
        for partner in self:
            domain = partner.compute_deposit_domain()
            deposit_ids = self.env["sale.order.line"].search(domain)
            partner.deposit_ids = deposit_ids
            partner.deposit_count = len(deposit_ids)

    deposit_count = fields.Integer(
        string="# of Deposits", compute="_compute_deposit_ids"
    )
    deposit_days = fields.Integer("Deposit days", default=30)
    deposit_ids = fields.One2many(
        "sale.order.line", compute="_compute_deposit_ids"
    )

    @api.multi
    def action_open_deposit(self):
        self.ensure_one()
        action = self.env.ref(
            "stock_deposit_custom.act_res_partner_2_deposit"
        ).read()[0]
        action["domain"] = self.compute_deposit_domain()
        return action
