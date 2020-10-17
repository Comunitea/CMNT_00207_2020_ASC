# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    active = fields.Boolean("Active", default=True)

    @api.multi
    def check_duplicate_lote_names(self):

        sql = "select max(id), name from stock_production_lot group by(name) having count(id)>1"
        self._cr.execute(sql)
        res = self._cr.fetchall()
        for lot in res:
            lot_id = self.browse(lot[0])
            body = "El número de serie <a href=#data-oe-model=stock.production.lot data-oe-id=%d>%s</a> está duplicado"% (lot[0], lot[1])
            lot_id.message_post(body=body,  subtype_id=self.env.ref('mail.mt_note').id)
            template = self.env.ref(
                "stock_custom.duplicate_lots_advise_partner", False
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
                    }
                )
            composer_id = self.env["mail.compose.message"].sudo(1).with_context(ctx).create({})
            values = composer_id.onchange_template_id(
                template.id, "comment", lot_id.name, lot_id.id
                )["value"]
            composer_id.write(values)
            composer_id.with_context(ctx).send_mail()

    @api.multi
    def deactivate_and_rename_lot(self):
        for lot in self:
            lot.write({"active": False, "name": "{}__{}".format("Archived", lot.name)})

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        return super(StockProductionLot, self).name_search(
            name.upper(), args=args, operator=operator, limit=limit
        )

    @api.model
    def create(self, vals):
        if vals.get("name"):
            vals["name"] = vals.get("name").upper()
        return super(StockProductionLot, self).create(vals)
