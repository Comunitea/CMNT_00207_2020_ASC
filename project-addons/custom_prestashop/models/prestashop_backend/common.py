# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, api


class PrestashopBackend(models.Model):
    _inherit = "prestashop.backend"

    _versions = {
        '1.5': 'prestashop.version.key',
        '1.6.0.9': 'prestashop.version.key.1.6.0.9',
        '1.6.0.11': 'prestashop.version.key.1.6.0.9',
        '1.6.1.23': 'prestashop.version.key.1.6.1.23',
        '1.6.1.2': 'prestashop.version.key.1.6.1.2'
    }

    @api.model
    def select_versions(self):
        """ Available versions

        Can be inherited to add custom versions.
        """
        return [
            ('1.5', '< 1.6.0.9'),
            ('1.6.0.9', '1.6.0.9 - 1.6.0.10'),
            ('1.6.0.11', '>= 1.6.0.11 - <1.6.1.2'),
            ('1.6.1.231', '=1.6.1.23'),
            ('1.6.1.2', '=1.6.1.2')
        ]

    def import_attributes(self):
        for backend_record in self:
            self.env[
                "prestashop.product.combination.option"
            ].with_delay().import_batch(backend_record)
        return True
