# © 2022 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api,fields, models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    def _assign_leads(self):
        self.ensure_one()
        if not self.email:
            return False
        email_leads = self.env['crm.lead'].search([('partner_id', '=', False), ('email_from', '=', self.email)])
        if email_leads:
            email_leads.write({'partner_id': self.id})
            return True
        return False

    def create_or_assign_lead(self):
        if not self._assign_leads():
            self.env['crm.lead'].create({
                'partner_id': self.id,
                'name': self.name,
                'type': 'opportunity'
            })
    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.team_id.automatic_leads:
            res.commercial_partner_id.create_or_assign_lead()
        res.with_delay().geo_localize()
        return res

    def write(self, vals):
        res = super().write(vals)
        for partner in self:
            if vals.get('team_id'):
                if not self.env['crm.lead'].search([('partner_id', 'child_of', partner.commercial_partner_id.id)]) and partner.team_id.automatic_leads:
                    partner.commercial_partner_id.create_or_assign_lead()
            if partner.customer and not partner.parent_id and partner.team_id.geolocation_active:
                if 'street' in vals or 'street2' in vals or 'city' in vals or 'state_id' in vals or 'country_id' in vals or 'zip' in vals:
                    partner.with_delay().geo_localize()
        return res
