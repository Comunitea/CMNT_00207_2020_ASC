
##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2020 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
#    Vicente Ángel Gutiérrez <vicente@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See thefire
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from odoo import api, fields, models
from odoo.tools import float_is_zero


_logger = logging.getLogger(__name__)


class ReportPrintBatchPicking(models.AbstractModel):
    _name = 'report.stock_picking_batch_extended.report_batch_picking'

    @api.model
    def _get_report_values(self, docids, data=None):
        model = 'stock.picking.batch'
        docs = self.env[model].browse(docids)
        try:
            self.env.ref("stock.action_report_delivery").print_document(
                docs.picking_ids._ids
            )
        except Exception:
            docs.message_post('Ha fallado la impresión del albarán')
