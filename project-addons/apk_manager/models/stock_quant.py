from odoo import api, fields, models, _
#from pprint import pprint
from .apk_manager import LIMIT
import logging
_logger = logging.getLogger(__name__)
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

class StockQuant(models.Model):
    _inherit = 'stock.quant'


    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        if self._context.get('force_lot_id',False):
            lot_id = self.env['stock.production.lot'].browse(self._context['force_lot_id'])

        return super()._get_available_quantity(
            product_id=product_id,
            location_id=location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
            allow_negative=allow_negative)


    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):

        ## ESTO LO HAGO PARA NO RESERVAR LOTES O SERIES
        quants = super()._gather(product_id=product_id, location_id=location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)    
        not_lot_id = self._context.get('not_lot_id', False) 
        not_loc_id = self._context.get('not_loc_id', False) 
        if not_lot_id:
            quants = quants.filtered(lambda x: x.lot_id not in not_lot_id)
        if not_loc_id:
            quants = quants.filtered(lambda x: x.location_id not in not_loc_id)
        return quants

        not_loc_id = self._context.get('not_location_id', False)

        if not not_lot_id and not not_loc_id:
            return super()._gather(product_id=product_id, location_id=location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        _logger.info("Entrando en QUANT _gather con %s"%self._context)
        removal_strategy = self._get_removal_strategy(product_id, location_id)
        removal_strategy_order = self._get_removal_strategy_order(removal_strategy)
        domain = [
            ('product_id', '=', product_id.id),
        ]
        if not strict:
            if lot_id:
                domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)], domain])
            elif not_lot_id:
                domain = expression.AND([[('lot_id', 'not in', not_lot_id.ids)], domain])
            if package_id:
                domain = expression.AND([[('package_id', '=', package_id.id)], domain])
            if owner_id:
                domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
            domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
        else:
            if lot_id:
                domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)]])
            elif not_lot_id:
                domain = expression.AND([[('lot_id', 'not in', not_lot_id.ids)], domain])
            else:
                domain = expression.AND ([[('lot_id', '=', False)], domain])
            domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
            domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])

        if not_loc_id:
            domain = expression.AND([[('location_id', 'not in', not_loc_id.ids)], domain])
            


        # Copy code of _search for special NULLS FIRST/LAST order
        self.sudo(self._uid).check_access_rights('read')
        query = self._where_calc(domain)
        self._apply_ir_rules(query, 'read')
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + " ORDER BY "+ removal_strategy_order
        self._cr.execute(query_str, where_clause_params)
        res = self._cr.fetchall()
        # No uniquify list necessary as auto_join is not applied anyways...
        quants = self.browse([x[0] for x in res])
        quants = quants.sorted(lambda q: not q.lot_id)
        return quants