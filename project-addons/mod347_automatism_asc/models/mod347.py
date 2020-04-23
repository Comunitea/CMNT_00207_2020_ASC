# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, exceptions, _
import datetime
from odoo.exceptions import ValidationError

class L10nEsAeatMod347Report(models.Model):
    _inherit = "l10n.es.aeat.mod347.report"

    def autogenerate_model347(self):
        now = datetime.datetime.now()
        year = now.year
        date_start = datetime.datetime.strptime('{}-01-01'.format(year), "%Y-%m-%d").date()
        for company in self.env['res.company'].search([]):
            if company.vat and company.phone:
                model347 = self.env['l10n.es.aeat.mod347.report'].search([
                    ('company_id', '=', company.id),
                    ('date_start', '=', '{}-01-01'.format(year)),
                    ('date_end', '=', '{}-12-31'.format(year)),
                    ('state', 'in', ['done', 'draft', 'calculated', 'posted']),
                    ('type', '=', 'N')
                ])
                if not model347:
                    model347 = self.env['l10n.es.aeat.mod347.report'].create({
                        'company_id': company.id,
                        'company_vat': company.vat,
                        'contact_phone': company.phone,
                        'contact_name': company.name,
                        'type': 'N',
                        'support_type': 'T',
                        'year': year,
                        'date_start': '{}-01-01'.format(year),
                        'date_end': '{}-12-31'.format(year),
                    })

                if model347.state in ['done']:
                    raise ValidationError(
                        _('The Model347 for this year is marked as done.'))

                model347.button_calculate()

                unnotified_partners = model347.partner_record_ids.filtered(lambda x: not x.partner_id.date_alert \
                    or x.partner_id.date_alert < date_start)
                
                for partner in unnotified_partners:
                    body = _('The payments amount for the partner {} is currently surpassing 6000€.'.format(
                        partner.partner_id.name)
                    )
                    partner.partner_id.message_post(body=body)
                    partner.partner_id.date_alert=datetime.datetime.now().date()
            else:
                raise ValidationError(
                    _('The company {} needs to have a valid VAT and phone.'.format(company.name)))