# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class DeliveryCarrier(models.Model):

    _inherit = "delivery.carrier"

    intrastat_transport_id = fields.Many2one(
        comodel_name='intrastat.transport_mode', string='Transport Mode',
        help="This information is used in Intrastat reports")
