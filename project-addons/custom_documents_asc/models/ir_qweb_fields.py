# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api
from odoo.tools import (
    html_escape as escape,
    posix_to_ldml,
    safe_eval,
    float_utils,
    format_date,
    pycompat,
)


class Contact(models.AbstractModel):
    _inherit = "ir.qweb.field.contact"

    @api.model
    def value_to_html(self, value, options):
        if not value.exists():
            return False

        opf = (
            options
            and options.get("fields")
            or ["name", "address", "phone", "mobile", "email"]
        )
        opsep = options and options.get("separator") or "\n"
        value = value.sudo().with_context(show_address=True)
        if options.get("commercial_data"):
            name_get = value.commercial_partner_id.name_get()[0][1]
        else:
            name_get = value.name_get()[0][1]

        val = {
            "name": name_get.split("\n")[0],
            "address": escape(opsep.join(name_get.split("\n")[1:])).strip(),
            "phone": value.phone,
            "mobile": value.mobile,
            "city": value.city,
            "country_id": value.country_id.display_name,
            "website": value.website,
            "email": value.email,
            "fields": opf,
            "object": value,
            "options": options,
            "vat": value.vat,
        }
        return self.env["ir.qweb"].render(
            "base.contact", val, **options.get("template_options")
        )
