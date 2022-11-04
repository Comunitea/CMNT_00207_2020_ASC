from odoo import api, fields, models, _


class UomUom(models.Model):
    _inherit = "uom.uom"

    wh_code = fields.Char('Apk Code', help="Code to use in app")

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):

        if self._context.get('from_pda', False):
            result = []
            for uom in self:
                result.append((uom.id, uom.wh_code))
            return result
        return super().name_get()
