# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class Image(models.Model):
    _inherit = "base_multi_image.image"

    file_db_store = fields.Binary(attachment=True)
