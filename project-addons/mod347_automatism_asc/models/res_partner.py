# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, exceptions, _
import datetime

class ResPartner(models.Model):
    _inherit = 'res.partner'

    date_alert = fields.Date()