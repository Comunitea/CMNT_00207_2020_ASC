# © 2022 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


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
        if res.customer and not res.parent_id and res.team_id.geolocation_active:
            res.with_delay().geo_localize()
        return res

    def write(self, vals):
        res = super().write(vals)
        for partner in self:
            if vals.get('team_id'):
                if not self.env['crm.lead'].search([('partner_id', 'child_of', partner.commercial_partner_id.id)]) and partner.team_id.automatic_leads:
                    partner.commercial_partner_id.create_or_assign_lead()
            if partner.team_id.geolocation_active and not partner.parent_id and partner.customer:
                if set(vals.keys()).intersection(['street', 'street2', 'city', 'state_id', 'country_id', 'zip']):
                    partner.with_delay().geo_localize()
        return res
