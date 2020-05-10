# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class PrestashopBackend(models.Model):
    _inherit = "prestashop.backend"

    def import_attributes(self):
        for backend_record in self:
            self.env[
                "prestashop.product.combination.option"
            ].with_delay().import_batch(backend_record)
        return True
