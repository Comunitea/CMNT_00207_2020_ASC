# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action


class ProductTemplate(models.Model):

    _inherit = "product.template"

    prestashop_id = fields.Char()
    
    @api.one
    def _set_standard_price(self):
        res = super()._set_standard_price()
        for record in self:
            self._event("on_standard_price_changed").notify(record)
        return res


class PrestashopProductTemplateListener(Component):
    _name = "prestashop.product.template.listener"
    _inherit = "base.event.listener"
    _apply_on = ["product.template"]

    def on_standard_price_changed(self, record):
        for binding in record.prestashop_bind_ids:
            binding.with_delay().export_standard_price()


class PrestashopProductTemplate(models.Model):
    _inherit = "prestashop.product.template"

    @job(default_channel="root.prestashop")
    @related_action(action="related_action_unwrap_binding")
    @api.multi
    def export_standard_price(self):
        """ Export the standard price of a product. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage="standard_price.exporter")
            return exporter.run(self)
