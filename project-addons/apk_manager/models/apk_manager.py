

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

import logging
_logger = logging.getLogger(__name__)


import sys
import threading
import traceback


import threading
import odoo
from datetime import date, datetime
from xmlrpc.client import dumps, loads
import xmlrpc.client

from werkzeug.wrappers import Response

from odoo.http import Controller, dispatch_rpc, request, route
from odoo.service import wsgi_server
from odoo.fields import Date, Datetime
from odoo.tools import lazy

import werkzeug.exceptions
import werkzeug.wrappers
import werkzeug.serving
import werkzeug.contrib.fixers


try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    # pylint: disable=bad-python3-import
    import xmlrpclib

LIMIT = 0

def wsgi_xmlrpc_ok(environ, start_response):
    """ Two routes are available for XML-RPC

    /xmlrpc/<service> route returns faultCode as strings. This is a historic
    violation of the protocol kept for compatibility.

    /xmlrpc/2/<service> is a new route that returns faultCode as int and is
    therefore fully compliant.
    """
    if environ["REQUEST_METHOD"] == "POST" and environ["PATH_INFO"].startswith(
        "/xmlrpc/"
    ):
        length = int(environ["CONTENT_LENGTH"])
        data = environ["wsgi.input"].read(length)

        # Distinguish betweed the 2 faultCode modes
        string_faultcode = True
        service = environ["PATH_INFO"][len("/xmlrpc/") :]
        if environ["PATH_INFO"].startswith("/xmlrpc/2/"):
            service = service[len("2/") :]
            string_faultcode = False

        params, method = xmlrpclib.loads(data)
        try:

            result = odoo.http.dispatch_rpc(service, method, params)
            response = xmlrpclib.dumps((result,), methodresponse=1, allow_none=False)

        except Exception as e:
            if string_faultcode:
                response =  wsgi_server.xmlrpc_handle_exception_string(e)
            else:
                response =  wsgi_server.xmlrpc_handle_exception_int(e)
        headers = [
                              ('Content-Type','text/xml'),('Content-Length', str(len(response))),
                              ('Access-Control-Allow-Origin','*'),
                              ('Access-Control-Allow-Methods','POST, GET, OPTIONS'),
                              ('Access-Control-Max-Age',1000),
                              ('Access-Control-Allow-Headers','origin, x-csrftoken, content-type, accept'),
                    ]
        return werkzeug.wrappers.Response(response=response, mimetype="text/xml", headers=headers)(
            environ, start_response)


class ApkManager(models.Model):
    _name = "apk.manager"


    @api.model_cr
    def _register_hook(self):
        ### 🐒-patch XML-RPC controller to know remote address.
        super()._register_hook()

        original_fn = wsgi_server.application_unproxied

        def _patch(environ, start_response):

            environ['HTTP_ORIGIN'] = environ['HTTP_REFERER'] = environ['HTTP_HOST']
            if hasattr(threading.current_thread(), "uid"):
                del threading.current_thread().uid
            if hasattr(threading.current_thread(), "dbname"):
                del threading.current_thread().dbname
            if hasattr(threading.current_thread(), "url"):
                del threading.current_thread().url
            with odoo.api.Environment.manage():
                if environ["REQUEST_METHOD"] == "POST" and environ["PATH_INFO"].startswith("/xmlrpc/"):
                    # _logger.info ("\n------------XMLRP\n" + environ['PATH_INFO'] + "\n-------------------")
                    # Try all handlers until one returns some result (i.e. not None).
                    result = wsgi_xmlrpc_ok(environ, start_response)
                    if result:
                        return result
            return original_fn(environ, start_response)

        wsgi_server.application_unproxied = _patch


class ApkModel(models.AbstractModel):
    _name = "apk.model"

    apk_name = fields.Char("Apk Name", help="Display name para la apk")
    wh_code = fields.Char(string="Unique WH Code")

    def get_selection_dict_values(self, field, value = False):
        selection = self.fields_get()[field]["selection"]
        if value:
            for key, val in selection:
                if key == value:
                    return {"value": key, "name": val}
        res = []
        for option in selection:
            res.append({"name": option[1], "value": option[0]})
        return res

    def return_filter(self, model, field):
        if self.fields_get()[field]["type"] == "selection":
            res = model.get_selection_dict_values(field, model[field])
        elif self.fields_get()[field]["type"] == "many2one":
            res = {'name' : model[field]['display_name'], 'value': model[field]['id']}
        else:
            res = {'name': model[field], 'value': model[field]}
        return [res]

    def get_filters(self, fields_to_filter):

        res_filter = []
        for f1 in fields_to_filter:
            values = []
            vals = []
            for pick in self:
                if pick[f1['field']] and pick[f1['field']] not in vals:
                    vals += [pick[f1['field']]]
                    values += self.return_filter(pick, f1['field'])

            res_filter += [{
                    'name': f1['name'],
                    'field': f1['field'],
                    'values': values}]
        return res_filter


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ["apk.model", "crm.team"]

    wh_code = fields.Char("Wh code")


class DeliveryCarrier(models.Model):
    _name = "delivery.carrier"
    _inherit = ["apk.model", "delivery.carrier"]

    wh_code = fields.Char("Wh code")