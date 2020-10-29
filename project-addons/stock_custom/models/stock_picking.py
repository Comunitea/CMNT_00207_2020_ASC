# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PickingTypeGroup(models.Model):
    _inherit = "picking.type.group.code"

    need_ready_to_send = fields.Boolean(
        string="Need PDA Ready",
        default=False,
        help="Si está marcado el alabrán necesitará una autorización para enviarse",
    )


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ready_to_send = fields.Boolean(string="PDA Ready", default=False, copy=False,)
    team_id = fields.Many2one("crm.team")
    move_type = fields.Selection(track_visibility='onchange')

    @api.depends(
        "ready_to_send", "move_type", "move_lines.state", "move_lines.picking_id"
    )
    @api.one
    def _compute_state(self):
        """ State of a picking depends on the state of its related stock.move
        - Draft: only used for "planned pickings"
        - Waiting: if the picking is not ready to be sent so if
          - (a) no quantity could be reserved at all or if
          - (b) some quantities could be reserved and the shipping policy is "deliver all at once"
        - Waiting another move: if the picking is waiting for another move
        - Ready: if the picking is ready to be sent so if:
          - (a) all quantities are reserved or if
          - (b) some quantities could be reserved and the shipping policy is "as soon as possible"
        - Done: if the picking is done.
        - Cancelled: if the picking is cancelled
        """
        if not self.move_lines:
            self.state = "draft"
        elif any(
            move.state == "draft" for move in self.move_lines
        ):  # TDE FIXME: should be all ?
            self.state = "draft"
        elif all(move.state == "cancel" for move in self.move_lines):
            self.state = "cancel"
        elif all(move.state in ["cancel", "done"] for move in self.move_lines):
            self.state = "done"
        else:
            relevant_move_state = self.move_lines._get_relevant_state_among_moves()
            if relevant_move_state == "partially_available":
                self.state = "assigned"
            else:
                self.state = relevant_move_state
            if (
                (
                    relevant_move_state == "partially_available"
                    or relevant_move_state == "assigned"
                )
                and (not self.ready_to_send and self.sale_id and self.picking_type_id.group_code.need_ready_to_send )
            ):
                self.state = "waiting"

    @api.multi
    def _create_backorder(self, backorder_moves=None):
        backorder = super()._create_backorder(backorder_moves=backorder_moves)
        backorder.write({"move_type": "one"})
        return backorder

    @api.multi
    def mark_as_ready_to_send(self):
        for pick in self:

            if pick.sale_id and not pick.sale_id.ready_to_send:
                raise UserError(_("You can not mark a picking with a sale order not ready to send manually."))
            elif pick.ready_to_send:
                raise UserError(_("Pick is already ready to send."))
            elif pick.picking_type_id.code != "outgoing":
                raise UserError(_("You can not mark as a ready to send an incoming picking."))
            else:
                pick.ready_to_send = True

    @api.model
    def check_assign_all(self):
        """ Try to assign confirmed pickings """
        domain = [
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "in", ["confirmed", "partially_available", "waiting"]),
        ]
        picking_ids = (
            self.env["stock.move"]
            .search(domain, order="date_expected")
            .mapped("picking_id")
        )
        picking_ids.action_assign()

