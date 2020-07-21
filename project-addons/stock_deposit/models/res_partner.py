##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    deposit_count = fields.Integer(string="# of Deposits", compute="_deposit_count")

    # lo pongo company depend por coeherencia con el property_stock_deposit
    property_deposit_days = fields.Integer(
        "Deposit days", default=30, company_dependent=True
    )
    property_stock_deposit = fields.Many2one(
        "stock.location",
        string="Deposit Location",
        company_dependent=True,
        help="This stock location will be used, as the destination location "
        "for goods you send to customer's deposit",
    )

    @api.multi
    def _deposit_count(self):
        for partner in self:
            if partner.active:
                deposit_ids = self.env["stock.deposit"].search(
                    [("partner_id", "child_of", [partner.id])]
                )
            else:
                deposit_ids = []

            partner.deposit_count = len(deposit_ids)
