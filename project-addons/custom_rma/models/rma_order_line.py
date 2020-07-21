# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class RmaOrderLine(models.Model):

    _inherit = "rma.order.line"

    @api.onchange("lot_id")
    def onchange_lot_id_custom(self):
        if self.lot_id:
            stock_moves = (
                self.env["stock.move.line"]
                .search(
                    [
                        ("lot_id", "=", self.lot_id.id),
                        ("state", "=", "done"),
                        ("move_id.sale_line_id", "!=", False),
                    ]
                )
                .mapped("move_id")
            )
            if not stock_moves:
                self.reference_move_id = None
                self.sale_line_id = None
                self.invoice_line_id = None
                return
            self.reference_move_id = stock_moves
            self.sale_line_id = stock_moves.sale_line_id
            self.invoice_line_id = (
                stock_moves.sale_line_id.invoice_lines
                and stock_moves.sale_line_id.invoice_lines[0]
            )

    @api.multi
    def _remove_other_data_origin(self, exception):
        return
