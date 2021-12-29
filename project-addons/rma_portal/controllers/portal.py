from collections import OrderedDict
from operator import itemgetter

from odoo import http, _, SUPERUSER_ID
from odoo.tools import config
from odoo.exceptions import AccessError, MissingError, AccessDenied
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.account.controllers.portal import PortalAccount
from odoo.addons.web.controllers.main import Home, ensure_db
from odoo.tools import groupby as groupbyelem
from datetime import date, datetime, timedelta

from odoo.osv.expression import OR


class CustomerPortal(CustomerPortal):

    def _login_redirect(self, uid, redirect=None):
        return redirect if redirect else '/my/home'

    @http.route('/web/login_prestashop', type='http', auth="none", sitemap=False, csrf=False)
    def web_login_prestashop(self, redirect=None, **kw):
        ensure_db()
        if request.params.get('presta_token'):
            # Se establece el username, y el token como password para la funcion _check_credentials
            presta_user = request.env['res.users'].search([('prestashop_access_token', '=', request.params['presta_token'])])
            request.params['login'] = presta_user.login
            request.params['password'] = request.params['presta_token']
            request.params['login_success'] = False
            if not request.uid:
                request.uid = SUPERUSER_ID

            values = request.params.copy()
            try:
                values['databases'] = http.db_list()
            except AccessDenied:
                values['databases'] = None

            old_uid = request.uid
            try:
                uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            except AccessDenied:
                request.uid = old_uid
        return http.local_redirect('/')

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['rma_count'] = request.env['rma.order'].search_count([])
        return values

    def _rma_get_page_view_values(self, rma, access_token, **kwargs):
        values = {
            'page_name': 'rma',
            'rma': rma,
        }
        return self._get_page_view_values(rma, access_token, values, 'my_rma_history', False, **kwargs)

    @http.route(['/my/rmas', '/my/rmas/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rmas(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Rma = request.env['rma.order']
        domain = []

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('rma.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        # rma count
        rma_count = Rma.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/rmas",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=rma_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        rma = Rma.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_rma_history'] = rma.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'rmas': rma,
            'page_name': 'rma',
            'archive_groups': archive_groups,
            'default_url': '/my/rma',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("rma_portal.portal_my_rmas", values)

    @http.route(['/my/rma/<int:rma_id>'], type='http', auth="public", website=True)
    def portal_my_rma(self, rma_id=None, access_token=None, report_type=None, download=False, **kw):
        try:
            rma_sudo = self._document_check_access('rma.order', rma_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=rma_sudo, report_type=report_type, report_ref='rma.rma_order_report', download=download)
        values = self._rma_get_page_view_values(rma_sudo, access_token, **kw)
        return request.render("rma_portal.portal_my_rma", values)

    @http.route(["/requestrma"], type="http", auth="user", website=True)
    def request_rma(self, **post):
        partners = request.env["res.partner"].search([])
        from_date_order = (datetime.now() + timedelta(days=-60)).date()
        orders = request.env['sale.order'].search([('date_order', '>=', from_date_order)])
        delivery_partners = partners.filtered(
            lambda rec: (rec and rec.type in ("delivery")) or not rec.parent_id
        )
        return request.render(
            "rma_portal.add_rma_portal",
            {
                "delivery_partners": delivery_partners,
                "orders": orders,
            },
        )

    @http.route(
        ["/my/add_rma_line"], type="json", auth="user", website=True, sitemap=False
    )
    def add_rma_line(self):
        orders = request.env["sale.order"].search([])
        products = False
        if orders:
            products = (
                orders.sudo()
                .mapped("order_line.product_id")
                .filtered(lambda prod: prod.type not in ("service") and not prod.pack_product)
            )
            packs = (
                orders.sudo()
                .mapped("order_line.product_id")
                .filtered(lambda prod: prod.pack_product)
            )
            products += packs.mapped('pack_components')
        result = request.env["ir.ui.view"].render_template(
            "rma_portal.rma_add_new_line",
            {"products": products},
        )
        return result

    @http.route(
        ["/my/check_order_date"], type="json", auth="user", website=True, sitemap=False
    )
    def check_order_date(self, order_ref):
        if order_ref:
            return request.env['rma.order'].check_sale_dates(order_ref)

    @http.route(
        ["/my/create_rma_obj"], type="json", auth="user", website=True, sitemap=False
    )
    def create_rma_obj(self, rma_obj=None, rma_line=None, shipping_data=None):
        return_delivery_address = False
        res = False
        if shipping_data.get("optVal") == -1:
            s_vals = {
                "type": "delivery",
                "parent_id": rma_obj.get("partner_id", False),
                "name": shipping_data.get("shipping_name", "Shipping 1"),
                "city": shipping_data.get("shipping_city", False),
                "zip": shipping_data.get("shipping_zip", False),
                "street": shipping_data.get("shipping_street", False),
                "phone": shipping_data.get("shipping_phone", False),
                "mobile": shipping_data.get("shipping_mobile", False),
                "comment": shipping_data.get("shipping_note", False),
                "email": shipping_data.get("shipping_email", False),
            }

            if shipping_data.get("shipping_state_id"):
                s_vals["state_id"] = shipping_data.get("shipping_state_id")
            else:
                s_vals["country_id"] = shipping_data.get("shipping_country_id", False)

            shiping_id = request.env["res.partner"].sudo().create(s_vals)
            return_delivery_address = shiping_id.id
        else:
            return_delivery_address = rma_obj.get("return_delivery_address", False)
        if rma_line:
            vals = {
                "partner_id": request.env.user.partner_id.id,
                "operation_type": rma_obj['operation_type'],
                "requested_by": request.env.user.id
            }
            if rma_obj['operation_type'] == 'return':
                vals['return_from_sale'] = rma_obj['order_id']
            else:
                pickup_date = rma_obj.get("pickup_date", False)
                pickup_hour = rma_obj.get("pickup_hour", False)
                hours, minutes = pickup_hour.split(':')
                hours = int(hours) + rma_obj['timezone']
                pickup_hour = '{}:{}'.format(hours, minutes)
                pickup_time = "{} {}".format(pickup_date, pickup_hour)
                pickup_time = datetime.strptime(pickup_time, '%d/%m/%Y %H:%M')
                vals['pickup_time'] = pickup_time
                vals['delivery_address_id'] = return_delivery_address
            res = request.env["rma.order"].sudo().create(vals)
            for line in rma_line:
                product_id = line.get("pid")

                if product_id == -1:
                    product_id = request.env.ref("rma_portal.product_unknow").id

                line_vals = {
                    "type": "customer",
                    "rma_id": res.id,
                    "invoice_ref": line.get('invoice'),
                    "product_id": product_id,
                    "informed_lot_id": line.get("searial_num"),
                    "uom_id": request.env.ref('uom.product_uom_unit').id,
                    "product_qty": line.get("qty", 1),
                    "description": line.get("note", '') + '\n' + line.get('invoice', ''),
                    "product_ref": line.get("product_ref"),
                    "partner_id": request.env.user.partner_id.id,
                }
                lot_exists = request.env['stock.production.lot'].sudo().search([
                    ('product_id', '=', product_id),
                    ('name', '=ilike', line.get("searial_num"))
                    ])
                if lot_exists:
                    line_vals['lot_id'] = lot_exists.id
                specs = request.env['rma.order.line']._onchange_spec()
                updates = request.env['rma.order.line'].sudo().onchange(line_vals, ['product_id'], specs)
                value = updates.get('value', {})
                for name, val in value.items():
                    if isinstance(val, tuple):
                        value[name] = val[0]
                line_vals.update(value)
                line_vals['operation_id'] = 5
                updates = request.env['rma.order.line'].sudo().onchange(line_vals, ['operation_id'], specs)
                value = updates.get('value', {})
                for name, val in value.items():
                    if isinstance(val, tuple):
                        value[name] = val[0]
                line_vals.update(value)
                request.env['rma.order.line'].sudo().create(line_vals)
        return res.ids
        # if res:
        #     print("llega")
        #     if res.operation_type == 'return':
        #         if (date.today() - res.order_id.date_order.date()).days > 30:
        #             return res.ids
        #     res.action_rma_approve()
        #     return res.ids
        # else:

        #     return False

    @http.route(
        ["/my/thanks_rma_msg"], type="http", auth="user", website=True, sitemap=False
    )
    def thanks_rma_msg(self, **post):
        rma_order = request.env["rma.order"].browse(int(post.get("rma_obj")))
        return request.render("rma_portal.thank_rma_msg", {"rma_order": rma_order})


class PortalAccountCustom(PortalAccount):

    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['account.invoice']

        domain = []

        searchbar_sortings = {
            'date': {'label': _('Invoice Date'), 'order': 'date_invoice desc'},
            'duedate': {'label': _('Due Date'), 'order': 'date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
        }
        # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('account.invoice', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        invoice_count = AccountInvoice.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/invoices",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        invoices = AccountInvoice.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_invoices_history'] = invoices.ids[:100]

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/invoices',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("account.portal_my_invoices", values)

    @http.route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
            return request.redirect('/my/home')
