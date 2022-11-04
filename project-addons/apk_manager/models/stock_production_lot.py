from odoo import api, fields, models, _
#from pprint import pprint
from .apk_manager import LIMIT
import logging
_logger = logging.getLogger(__name__)
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

class VirtualProductionLot(models.Model):
    _inherit = 'virtual.serial'

    def get_def_values(self):
        return {'id': self.id,
                'name': self.name}
    
class StockProductionLot(models.Model):

    _inherit = "stock.production.lot"

    active = fields.Boolean('Active', default=True)

    def get_def_values(self):
        return {'id': self.id,
                'name': self.name}


    def get_available_lot(self, where_id_moves, location_id = 1, product_ids = [],  model = 'stock.move'):
        ## MULTICOMPAÑIA. SUPONGO LAS COMPAÑIAS POR LA UBICACIO
        ## debe devolver un listado 2 dos columna product columna array de series disponibles para ese producto
        ## Además elimina los repetidos
        company_id = self.env.user.company_id.id
        loc_sql = """
                    select id from stock_location where (company_id is null or company_id = %s) and parent_path ilike (select parent_path from stock_location where id=%s) || '%'
                    """%(company_id, location_id)

        if model == 'stock.picking.batch':
            product_sql ="""select product_id from stock_move_line sm
                            join stock_picking sp on sp.id = sm.picking_id
                            where sm.state not in
                            ('draft', 'cancel', 'done') and sp.batch_id = %s
                            """%where_id_moves

        elif model == 'stock.move':
            product_sql ="""select product_id from stock_move_line
                            where state not in
                            ('draft', 'cancel', 'done') and move_id = %s
                            """%where_id_moves

        elif model == 'stock.picking':
             product_sql ="""select product_id from stock_move_line
                            where state not in
                            ('draft', 'cancel', 'done') and picking_id = %s
                            """%where_id_moves
        else :
            product_sql = """(%)"""%','.join(product_ids)

        sql = """
                with result as (select product_id, id from stock_production_lot spl
                                where location_id in (%s) and product_id in (%s)
                        and name in (%s)
                        and active = true
                        and name not in (select name from stock_production_lot group by name having count(name) >1)
                        and spl.virtual_tracking = true order by id asc)

                SELECT r1.product_id, ARRAY(
                    SELECT r2.id::text FROM result r2 where r1.product_id = r2.product_id
                    )
                from result r1
                group by r1.product_id
                """
        self.cr.execute(sql, (loc_sql, product_sql, ','.join(lot_names)))
        res = self.cr.fetchall()
        return res
