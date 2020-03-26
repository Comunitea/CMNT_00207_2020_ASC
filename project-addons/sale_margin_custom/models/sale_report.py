# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    perc_margin = fields.Float("Margin (%)")

    def _select(self):
        return super(SaleReport, self)._select() + ", s.perc_margin AS margin"
