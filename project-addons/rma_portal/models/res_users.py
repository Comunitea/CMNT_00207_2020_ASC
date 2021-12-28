# © 2021 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import AccessDenied
import secrets
from odoo.tools import email_split


def extract_email(email):
    """ extract the email address from a user-friendly email address """
    addresses = email_split(email)
    return addresses[0] if addresses else ''


class ResUsers(models.Model):

    _inherit = 'res.users'

    prestashop_access_token = fields.Char()

    _sql_constraints = [
        ('prestashop_access_token_uniq',
         'unique(prestashop_access_token)',
         'Access token must be unique !'),
    ]

    @api.model
    def get_user_token(self, prestashop_customer_id):
        existing_partner = self.env['prestashop.res.partner'].search(
            [('prestashop_id', '=', prestashop_customer_id)]).odoo_id
        if not existing_partner:
            return False
        if not existing_partner.user_ids:
            self.env['res.users'].sudo().with_context(no_reset_password=True)._create_user_from_template({
                'email': extract_email(existing_partner.email),
                'login': extract_email(existing_partner.email),
                'partner_id': existing_partner.id,
                'company_id': self.env.user.company_id.id,
                'company_ids': [(6, 0, [self.env.user.company_id.id])],
            })
            # existing_partner.refresh()
        if not existing_partner.user_ids[0].prestashop_access_token:
            existing_partner.user_ids[0].generate_prestashop_token()
        return existing_partner.user_ids[0].prestashop_access_token

    @api.multi
    def generate_prestashop_token(self):
        self.ensure_one()
        self.prestashop_access_token = secrets.token_hex()

    def _check_credentials(self, password):
        try:
            res = super()._check_credentials(password)
            return res
        except AccessDenied:
            if self.env.user.prestashop_access_token != password:
                raise AccessDenied()
