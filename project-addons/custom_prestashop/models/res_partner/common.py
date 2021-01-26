# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.addons.queue_job.job import job
import logging
_logger = logging.getLogger(__name__)
try:
    from prestapyt import PrestaShopWebServiceError
except:
    _logger.debug('Cannot import from `prestapyt`')


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        country_id = vals.get('country_id', False)
        if country_id and country_id == self.country_id.id:
            del vals['country_id']
        return super().write(vals)


class PrestashopResPartner(models.Model):
    _inherit = "prestashop.res.partner"

    @job(default_channel="root.prestashop")
    def import_customers_since(
        self, backend_record=None, since_date=None, **kwargs
    ):
        """ Prepare the import of partners modified on PrestaShop """
        filters = {}
        if since_date:
            filters = {"date": "1", "filter[date_upd]": ">[%s]" % since_date}
        now_fmt = fields.Datetime.now()
        self.env["prestashop.res.partner.category"].import_batch(
            backend=backend_record, filters=filters, priority=10, **kwargs
        )
        filters["filter[f_pago]"] = "[1,2]"
        self.env["prestashop.res.partner"].import_batch(
            backend=backend_record, filters=filters, priority=15, **kwargs
        )
        backend_record.import_partners_since = now_fmt
        return True

    def resync(self):
        for address in self.mapped(
            "odoo_id.child_ids.prestashop_address_bind_ids"
        ) + self.mapped("odoo_id.prestashop_address_bind_ids"):
            try:
                address.resync()
            except PrestaShopWebServiceError:
                pass
        return super().resync()
