# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    risk_invoice_draft = fields.Monetary(store=False)
    risk_invoice_open = fields.Monetary(store=False)
    risk_invoice_unpaid = fields.Monetary(store=False)
    risk_account_amount = fields.Monetary(store=False)
    risk_account_amount_unpaid = fields.Monetary(store=False)
    risk_sale_order = fields.Monetary(store=False)
    risk_invoice_draft_include = fields.Boolean(default=True)
    risk_invoice_open_include = fields.Boolean(default=True)
    risk_invoice_unpaid_include = fields.Boolean(default=True)
    risk_account_amount_include = fields.Boolean(default=True)
    risk_account_amount_unpaid_include = fields.Boolean(default=True)
    risk_sale_order_include = fields.Boolean(default=True)
    risk_invoice_unpaid_limit = fields.Float(default=0.01)
