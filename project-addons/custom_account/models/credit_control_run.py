# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class CreditControlRun(models.Model):

    _inherit = "credit.control.run"

    @api.model
    def cron_credit_control_run(self):
        credit_control_run = self.env["credit.control.run"].create(
            {
                "date": fields.Date.today(),
                "policy_ids": [
                    (4, x.id)
                    for x in self.env["credit.control.policy"].search([])
                ],
            }
        )
        credit_control_run.generate_credit_lines()
        credit_control_lines = self.env["credit.control.line"].search(
            [
                ("run_id", "=", credit_control_run.id),
                ("move_line_id.payment_mode_id.credit_control", "=", True),
            ]
        )
        if credit_control_lines:
            credit_control_lines.write({'state': 'to_be_sent'})
            emailer = self.env['credit.control.emailer'].create({
                'line_ids': [(6, 0, credit_control_lines._ids)]
            })
            emailer.email_lines()
