# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, exceptions, _


class PrestashopImportCustomer(models.TransientModel):
    _name = "prestashop.import.customer"

    prestashop_id = fields.Integer(string="Id", required=True)

    @api.multi
    def import_customer(self):
        backend_ids = self.env["prestashop.backend"].browse(
            self.env.context.get("active_ids")
        )
        for backend in backend_ids:
            self.env["prestashop.res.partner"].with_delay().import_record(
                backend, self.prestashop_id
            )

        return {"type": "ir.actions.act_window_close"}
