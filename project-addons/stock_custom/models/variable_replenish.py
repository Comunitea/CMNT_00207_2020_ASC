# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api


class VariableReplenish(models.Model):
    _name = "variable.replenish"

    name = fields.Char("Name", required=True)
    min_qty = fields.Integer("Min quantity", required=True)
    max_qty = fields.Integer("Max quantity", required=True)
    sale_days = fields.Integer("Sale days", required=True)

    use_gt = fields.Boolean("Use + changes")
    gt_sales = fields.Integer("If sales")
    gt_days = fields.Integer("If days")
    gt_qty = fields.Integer("If qty")

    use_lt = fields.Boolean("Use - changes")
    lt_sales = fields.Integer("If sales")
    lt_days = fields.Integer("If days")
    lt_qty = fields.Integer("If qty")

    average_ratio = fields.Float("Average ratio", default=2)
    min_qty_ratio = fields.Float("Min qty ratio", default=0.6)

    send_cancel_mail = fields.Boolean("Send cancel mail", default=False, help="If checked, send an advice mail if outgoing pick is canceled")
    days_to_second_orderpoint = fields.Integer("Días para 2º Proveedor", default=3)
    quantity_per_cent = fields.Integer("% en segundo pedido", default=50)

    qty_field = fields.Selection([('product_uom_qty', 'Cant. Pedida'), ('qty_delivered', 'Cant. Entregada')], 
    "Sale line qty field", default="product_uom_qty")