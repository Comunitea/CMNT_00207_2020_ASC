from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)



class StockLocation(models.Model):
    _name = "stock.location"
    _inherit = ["apk.model", "stock.location"]


    def name_get(self):

        ## Para la PDA necesito un display_name para poder buscar en nombre y CDB
        if self._context.get('get_select', False):
            ret_list = []
            for location in self:
                if location.barcode:
                    name = "%s - %s"%(location.name, location.barcode)
                else:
                    name = location.name
                ret_list.append((location.id, name ))
            return ret_list
        ## Para mostrar en la PDA me llega con el nombre de la estantería, ya que el nombre largo es muy largo
        if self._context.get('short_name', False):
            ret_list = []
            for location in self:
                ret_list.append((location.id, location.name))
            return ret_list
        return super().name_get()

    @api.multi
    @api.depends('removal_priority')
    def _compute_removal_priority_char(self):
        for loc in self:
            loc.removal_priority_char = '%d' % loc.removal_priority

    @api.multi
    @api.depends('child_ids')
    def _compute_no_child_ids(self):
        for loc in self:
            loc.no_child_ids = loc.child_ids == self.env['stock.location']

    is_box = fields.Boolean('Is Box', default=False, help='If checked, is dest location for batch pickings. Customer usage')
    removal_priority_char = fields.Char(string='Removal Priority', compute=_compute_removal_priority_char, store=True)
    color = fields.Integer(string="Color Box")
    # TODO compute
    no_child_ids = fields.Boolean("No childs", default=False)## compute="_compute_no_child_ids", store=True)


    def get_def_values(self):
        return {
            'id': self.id,
            'barcode': self.barcode,
            'name': self.name,
        }

    @api.model
    def get_apk_location_list(self, values={}):
        domain = ['|', ('usage', '=', 'internal'), ('is_box', '=', True)]
        res = {}
        location_ids = self.search(domain)
        for location in location_ids:
            res[location.name] = location.barcode
        return res

    @api.model
    def get_apk_values(self, values={}):
        if values:
            id = values.get('picking_type_id', False)
        if not self:
            self.browse(id)
        values = {
            'id': self.id,
            'barcode': self.barcode,
            'name': self.name,
        }
        return values
    def return_dict_data(loc):
        return {
                'id': loc.id,
                'name': loc.name,
                'barcode': loc.barcode,
                'usage': loc.usage,
                'removal_priority': loc.removal_priority,
                'parent_path': loc.parent_path,
                'no_child_ids': loc.no_child_ids,
                'is_box': loc.is_box
            }
    @api.model
    def get_apk_locations(self, values={}):
        domain = values.get('domain', [])
        loc_ids = self.env['stock.location'].search(domain)
        vals = {}
        for loc in loc_ids:
            vals[loc.barcode] = loc.return_dict_data()
        return vals

    @api.model
    def LocationData(self, values):
        domain = values.get('domain', [('barcode', '!=', False)])
        Res = []
        # _logger.info("RECUERANCOD UBICACIONES CON %s"%domain)
        for loc in self.search(domain):
            vals= loc.return_dict_data()
            Res.append(vals)
        # _logger.info("Devuelvo %d ubicaciones"%len(Res))
        return Res
