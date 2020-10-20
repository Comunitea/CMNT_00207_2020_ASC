# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api

import logging

_logger = logging.getLogger(__name__)

class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    duplicate = fields.Boolean("Duplicate", default=False)
    ignore_duplicates = fields.Boolean("Ignorar check de duplicado", default = False)

    @api.multi
    def check_duplicate_lote_names(self):
        update ="update stock_production_lot set duplicate = false where duplicate = true"
        self._cr.execute(update)
        sql = "select max(id), min(id) from stock_production_lot where ignore_duplicates = false group by(name) having count(id)>1 order by name"
        self._cr.execute(sql)
        res = self._cr.fetchall()
        if not res:
            return
        lot_ids = self.env['stock.production.lot']
        msg = []
        for lot in res:
            lot_id = self.browse(lot[0])
            lot_ids += lot_id
            _logger.info ("El número de serie {} ({}) esta duplicado".format(lot_id.name, lot_id.id))
            body = "El número de serie <a href=#data-oe-model=stock.production.lot data-oe-id=%d>%s</a> está duplicado"% (lot_id.id, lot_id.name)
            msg += ["<a href=#data-oe-model=stock.production.lot data-oe-id=%d>%s</a>"% (lot_id.id, lot_id.name)]
            lot_id.message_post(body=body, subtype_id=self.env.ref('mail.mt_note').id)

            lot_id = self.browse(lot[1])
            lot_ids += lot_id
            _logger.info("El número de serie {} ({}) esta duplicado".format(lot_id.name, lot_id.id))
            body = "El número de serie <a href=#data-oe-model=stock.production.lot data-oe-id=%d>%s</a> está duplicado" % (
            lot_id.id, lot_id.name)
            msg += ["<a href=#data-oe-model=stock.production.lot data-oe-id=%d>%s</a>" % (lot_id.id, lot_id.name)]
            lot_id.message_post(body=body, subtype_id=self.env.ref('mail.mt_note').id)


        template = self.env.ref(
            "production_lot_duplicate_advice.duplicate_lots_advise_partner", False
        )
        ctx = dict(self._context)
        ctx.update(
            {
                    "default_model": "stock.production.lot",
                    "default_res_id": lot_id.id,
                    "default_use_template": bool(template.id),
                    "default_template_id": template.id,
                    "default_composition_mode": "comment",
                    "mark_so_as_sent": True,
                    "lot_ids": lot_ids,
                }
            )

        print (ctx)
        lot_ids.write({'duplicate': True})
        composer_id = self.env["mail.compose.message"].sudo().with_context(ctx).create({})
        values = composer_id.onchange_template_id(
            template.id, "comment", lot_id.name, lot_id.id
        )["value"]
        composer_id.write(values)
        composer_id.with_context(ctx).send_mail()

