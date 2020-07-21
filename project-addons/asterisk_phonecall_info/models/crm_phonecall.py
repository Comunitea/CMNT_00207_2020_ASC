# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CrmPhonecall(models.Model):
    _inherit = "crm.phonecall"

    extension = fields.Char("Extension")
    length = fields.Float("Length")
    notes = fields.Char("Notes")
    asterisk_id = fields.Char()

    # duplicated data
    tag_ids = fields.Many2many(
        comodel_name="crm.lead.tag",
        relation="crm_phonecall_tag_rel",
        column1="phone_id",
        column2="tag_id",
        string="Tags",
    )
    duration = fields.Float(help="Duration in minutes and seconds.")
    campaign_id = fields.Many2one("utm.campaign", "Campaing", readonly=True)
    source_id = fields.Many2one(
        "utm.source",
        string="Source",
        help="This is the link source, e.g. Search Engine, another domain,or name of email list",
        default=lambda self: self.env.ref("utm.utm_source_newsletter", False),
    )
    medium_id = fields.Many2one(
        "utm.medium",
        string="Medium",
        help="This is the delivery method, e.g. Postcard, Email, or Banner Ad",
        default=lambda self: self.env.ref("utm.utm_medium_email", False),
    )
