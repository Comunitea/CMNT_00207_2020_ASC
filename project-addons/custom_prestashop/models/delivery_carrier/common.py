# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class DeliveryCarrier(models.Model):

    _inherit = "delivery.carrier"

    prestashop_unique_id = fields.Char()
