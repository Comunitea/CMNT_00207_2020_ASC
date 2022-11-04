from odoo import api, fields, models, _


class DeliveryCrrier(models.Model):
    _inherit = "delivery.carrier"

    wh_code = fields.Char('Apk Code', help="Code to use in app")
