# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError


class RmaOrderLine(models.Model):

    _inherit = "rma.order.line"
    informed_lot_id = fields.Char()
    operation_id = fields.Many2one(readonly=False, states={})
    refund_policy = fields.Selection(readonly=False, states={})
    receipt_policy = fields.Selection(readonly=False, states={})
    delivery_policy = fields.Selection(readonly=False, states={})
    sale_policy = fields.Selection(readonly=False, states={})

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
                    ], limit=1, order="id desc"
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

    def action_rma_approve(self):
        if self.product_tracking in ("lot", "serial") and not self.lot_id:
            raise UserError(_("Serial number required"))
        res = super().action_rma_approve()
        wizard = (
            self.env["rma_make_picking.wizard"]
            .with_context(
                picking_type="incoming",
                active_ids=self._ids,
                active_model="rma.order.line",
            )
            .create({})
        )
        wizard.item_ids.write({"qty_to_receive": 1})
        wizard.action_create_picking()
        self.mapped("move_ids.picking_id").button_validate()
        return res

    @api.onchange("reference_move_id")
    def _onchange_reference_move_id(self):
        pass

    @api.multi
    @api.constrains("invoice_line_id", "partner_id")
    def _check_invoice_partner(self):
        for rec in self:
            if (
                rec.invoice_line_id
                and rec.invoice_line_id.invoice_id.partner_id != rec.partner_id
                and rec.reference_move_id.picking_id.partner_id not in self.env['res.partner'].search([('id', 'child_of', [rec.partner_id.id])])
            ):
                raise ValidationError(
                    _(
                        "RMA customer and originating invoice line customer "
                        "doesn't match."
                    )
                )

    @api.multi
    @api.constrains("reference_move_id", "partner_id")
    def _check_move_partner(self):
        for rec in self:
            if (
                rec.reference_move_id
                and rec.reference_move_id.picking_id.partner_id != rec.partner_id
                and rec.reference_move_id.picking_id.partner_id not in self.env['res.partner'].search([('id', 'child_of', [rec.partner_id.id])])
            ):
                raise ValidationError(
                    _(
                        "RMA customer and originating stock move customer "
                        "doesn't match."
                    )
                )
