from odoo import models, fields, api


class SaleOrder(models.Model):

    _inherit = "sale.order"


    @api.multi
    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        
        if self.team_id.invoice_on_company:
            res['ic_sale_id'] = self.id
        return res