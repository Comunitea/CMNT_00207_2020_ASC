##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2019 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
#    Vicente Ángel Gutiérrez <vicente@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, models, fields, modules
from contextlib import closing


import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"
    _order = "name asc"

    carrier_weight = fields.Float(default=0)
    carrier_packages = fields.Integer(default=0)
    carrier_id = fields.Many2one("delivery.carrier", "Carrier", ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Empresa")
    picking_ids = fields.One2many(
        string="Pickings",
        readonly=True,
        states={"draft": [("readonly", False)], "assigned": [("readonly", False)]},
        help="List of picking managed by this batch.",
    )
    team_id = fields.Many2one("crm.team")
    try_validate = fields.Boolean("Validación desde PDA", default=False)
    need_package = fields.Boolean(related="picking_type_id.group_code.need_package")
    need_weight = fields.Boolean(related="picking_type_id.group_code.need_weight")

    def mark_as_pda_validate(self):
        with api.Environment.manage():
            registry = modules.registry.Registry(self.env.cr.dbname)
            with closing(registry.cursor()) as cr:
                try:
                    sql = "update stock_picking_batch set try_validate = true where id = {}".format(
                        self.id
                    )
                    cr.execute(sql)
                except:
                    cr.rollback()
                    raise
                else:
                    # Despite what pylint says, this a perfectly valid
                    # commit (in a new cursor). Disable the warning.
                    cr.commit()  # pylint: disable=invalid-commit

    @api.model
    def button_validate_apk(self, vals):
        batch_id = self.browse(vals.get("id", False))
        if not batch_id:
            raise ValidationError("No se ha encontrado el albarán ")
        batch_id.mark_as_pda_validate()
        if batch_id.picking_type_id.group_code:
            g_code = batch_id.picking_type_id.group_code
            if g_code.need_weight and batch_id.carrier_weight == 0.00:
                raise ValidationError("Rellena el peso del albarán")
            if g_code.need_package and batch_id.carrier_packages == 0:
                raise ValidationError("Rellena el número de bultos")
        return super().button_validate_apk(vals)

    def return_fields(self, mode="tree"):
        res = super().return_fields(mode=mode)
        res += ["carrier_id", "team_id", "try_validate"]
        if mode == "form":
            res += ["carrier_weight", "carrier_packages", "need_package", "need_weight"]
        return res

    def get_model_object(self, values={}):

        res = super().get_model_object(values=values)
        picking_id = self
        if values.get("view", "tree") == "tree":
            return res
        if picking_id.state == "draft":
            picking_id.state = "in_progress"
            picking_id.user_id = self.env.user
        if not picking_id:
            if not picking_id or len(picking_id) != 1:
                return res
        values = {
            "domain": self.get_move_domain_for_picking(
                values.get("filter_moves", "Todos"), picking_id
            )
        }
        res["move_lines"] = self.env["stock.move"].get_model_object(values)
        return res

    @api.model
    def get_picking_list(self, values):
        domain = values.get("domain", [])
        filter_values = values.get("filter_values", {})
        ## AÑADO DOMINIO POR STATE
        filter_crm_team = filter_values.get("filter_crm_team", "")
        if filter_crm_team:
            team_ids = self.env["crm.team"].search_read(
                [("wh_code", "in", filter_crm_team)], ["id"]
            )
            domain += [("batch_id.team_id", "in", [x["id"] for x in team_ids])]
        filter_delivery_carrier = filter_values.get("filter_delivery_carrier", "")
        if filter_delivery_carrier:
            team_ids = self.env["delivery.carrier"].search_read(
                [("wh_code", "in", filter_delivery_carrier)], ["id"]
            )
            domain += [("batch_id.carrier_id", "in", [x["id"] for x in team_ids])]
        values["domain"] = domain
        return super().get_picking_list(values)

    @api.multi
    def regenerate_batch_notes(self):
        batches = self.env["stock.picking.batch"].search([])
        for batch_id in batches:
            notes = False
            for pick in batch_id.picking_ids:
                if pick.note and notes:
                    notes = "{} // {}: {}".format(notes, pick.name, pick.note)
                elif pick.note and not notes:
                    notes = "{}: {}".format(pick.name, pick.note)
                else:
                    sale_id = self.env["sale.order"].search(
                        [("name", "=", pick.origin)]
                    )
                    if sale_id and sale_id.note and notes:
                        notes = "{} // {}: {}".format(notes, pick.name, sale_id.note)
                    elif sale_id and sale_id.note and not notes:
                        notes = "{}: {}".format(notes, pick.name, sale_id.note)
            batch_id.notes = notes