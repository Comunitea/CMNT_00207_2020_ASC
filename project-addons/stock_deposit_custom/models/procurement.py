# Copyright 2019 Comunitea - Kiko Sánchez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_custom_move_fields(self):
        custom_move_fields = super(StockRule, self)._get_custom_move_fields()
        custom_move_fields += ["deposit_line_id"]
        return custom_move_fields
