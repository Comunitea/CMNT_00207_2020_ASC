# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Documents customizations for A-sec",
    "version": "12.0.1.0.0",
    "summary": "",
    "category": "custom",
    "author": "Comunitea",
    "maintainer": "Comunitea",
    "website": "www.comunitea.com",
    "license": "AGPL-3",
    "depends": [
        "base",
        "web",
        "sale_stock",
        "purchase",
        "rma_sale",
        "stock_picking_report_valued",
        "crm_claim",
        "product",
        "stock",
        "stock_available_unreserved",
        "account_due_dates_str",
        "stock_picking_batch_delivery_carrier_base",
        "stock_custom",
    ],
    "data": [
        "views/report_templates.xml",
        "views/crm_team.xml",
        "views/ir_qweb_widget_templates.xml",
        "views/rma_report_templates.xml",
        "views/purchase_order_templates.xml",
        "views/report_invoice.xml",
        "views/stock_picking_report_valued.xml",
        "views/crm_class.xml",
        "security/ir.model.access.csv",
        "views/stock.xml",
        "views/purchase_order.xml",
        "views/res_partner.xml",
        "views/sale_report.xml",
        "views/report_invoice_amz.xml"
    ],
}
