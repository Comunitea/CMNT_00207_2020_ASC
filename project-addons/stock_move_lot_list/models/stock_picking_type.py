# © 2018 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class StcokPickingType(models.Model):
    _inherit = "stock.picking.type"

    use_proposed_lots = fields.Boolean(
        "Lot list",
        help="If set, action confirm limitsearch to proposed lots",
        default=False,
    )
