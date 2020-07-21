# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, exceptions, _


class AccountAccount(models.Model):

    _inherit = "account.account"

    @api.constrains("code")
    def check_account_code(self):
        for acc in self:
            if not acc.code.isdigit():
                raise exceptions.ValidationError(_("Code of accounts must be numeric"))
            code = ""
            found = False
            for char in acc.code:
                code += char
                res = self.env["mis.report.kpi.expression"].search(
                    [
                        "|",
                        ("name", "=like", "%[" + code + "\%%"),
                        ("name", "=like", "%," + code + "\%%"),
                    ],
                    limit=1,
                )
                if res:
                    found = True
                    break
            if not found:
                raise exceptions.ValidationError(
                    _(
                        "Code doesn't seems valid because "
                        "it doesn't appear in any mis report."
                    )
                )
