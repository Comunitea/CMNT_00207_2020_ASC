from odoo import api, fields, models, _
#from pprint import pprint
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging
_logger = logging.getLogger(__name__)

class StockPickingType(models.Model):

    _inherit = "stock.picking.type"

    need_picking = fields.Boolean("Need previuous picking", default=False)
    merge_in_batch = fields.Boolean("Merge in prev. picking", default=False)
    is_only_for_picking = fields.Boolean("Only for picking", default=False)
    count_pick_group_ready = fields.Integer('Pick Group Ready', compute="compute_pick_group")
    count_pick_group_late = fields.Integer('Pick Group Late', compute="compute_pick_group")
    
    def get_pick_group_domains(self):
        return {
            'count_pick_group_ready': [('state', '!=', 'picked'), ('picking_type_id', 'in', self.ids)], 
            'count_pick_group_late': [('scheduled_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', '!=', 'picked'), ('picking_type_id', 'in', self.ids)]
        }

    @api.multi
    def compute_pick_group(self):
        domains = self.get_pick_group_domains()
        for field in domains:
            data = self.env['pick.group'].read_group(domains[field], ['picking_type_id'], ['picking_type_id'])
            count = {
                x['picking_type_id'][0]: x['picking_type_id_count']
                for x in data if x['picking_type_id']
            }
            for record in self:
                record[field] = count.get(record.id, 0)

    @api.multi
    def get_action_pick_group_ready(self):
        return self.get_action_pick_group_tree('count_pick_group_ready')
        
    @api.multi
    def get_action_pick_group_late(self):
        return self.get_action_pick_group_tree('count_pick_group_late')

    @api.multi
    def get_action_pick_group_tree(self, field):
        action = self._get_action(
            "apk_manager_pick_group.action_pick_group_form"
        )
        action["domain"] = self.get_pick_group_domains()[field] + [("picking_type_id", "in", self.ids)]
        return action

    @api.model
    def get_apk_info(self, values):
        res_all = super().get_apk_info(values)
        domain = [('app_integrated', '=', True), ('is_only_for_picking', '=', True)]
        for type in self.search(domain):
            res = {
                'id': type.id,
                'name': type.name,
                'location_id': type.default_location_src_id and {'id': type.default_location_src_id.id, 'name': type.default_location_src_id.name } or False,
                'count_picking_batch_ready': type.count_pick_group_ready,
                'count_picking_waiting': 0,
                'count_picking_late': type.count_pick_group_late,
                'count_picking_ready': 0,
                'count_picking_backorders': 0,
                'code': type.sequence_id.code
            }
            res_all.append(res)
        return res_all
