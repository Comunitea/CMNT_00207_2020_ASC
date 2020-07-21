# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AutomaticWorkflowJob(models.Model):

    _inherit = "automatic.workflow.job"
    _description = (
        "Scheduler that will play automatically the validation of"
        " invoices, pickings..."
    )

    def _do_validate_invoice(self, invoice):
        invoice = invoice.with_context(bypass_risk=True)
        return super()._do_validate_invoice(invoice)
