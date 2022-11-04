# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import unicodedata
# from odoo.tools.float_utils import float_compare
PRODUCT_VALUES= ['id', 'default_code', 'name', 'display_name']
LOCATION_VALUES = ['id', 'barcode', 'name', 'display_name', 'usage', 'parent_path', 'no_child_ids']


"""
    line_id = fields.Many2one('stock.serial.inventory.line', string="Line")
    location_id = fields.Many2one(related="line_id.location_id")
    product_id = fields.Many2one(related="line_id.product_id")
    serial_id = fields.Many2one('stock.production.lot') ##, domain=[('real_location_id', '=', location_id), ('virtual_tracking', '=', True)])
    name = fields.Char(string='name')
    to_delete =
"""
class SerialInventoryLine(models.Model):
    _inherit ="stock.serial.inventory.line"



class SerialInventory(models.Model):
    _inherit = "stock.serial.inventory"


    def get_apk_values(self):
        serial_ids = self.line_ids.mapped('serial_ids')
        serial_vals = []
        for serial in serial_ids:
            serial_vals += [{
                'id': serial.id,
                'serial_id': serial.serial_id and serial.serial_id.id or False,
                'name': serial.name,
                'to_delete': serial.to_delete
            }]
        return {
            'id': self.id, 
            'name': self.name,
            'product_id': {'id': self.product_id.id, 'default_code': self.product_id.default_code},
            'location_id': {'id': self.location_id.id, 'name': self.location_id.name},
            'serial_ids': serial_vals,
            'update_quant_qty': self.update_quant_qty

        }

    @api.model
    def load_serial_inventory(self, values):
        product_id = values.get('product_id')
        location_id = values.get('location_id')
        inventory_id = values.get('inventory_id')
        if inventory_id:
            domain = [('id', '=', inventory_id)]
        else:
            domain = [('product_id', '=', product_id), ('location_id', '=', location_id), ('state', '=', 'confirm')]
        inventory_id = self.env['stock.serial.inventory'].search(domain, limit=1)
        if not inventory_id:
            vals = {
                'location_id': location_id, 'product_id': product_id, 'name': "APK"
            }
            inventory_id = self.create(vals)
            inventory_id.name = 'APK: {} en {}'.format(inventory_id.product_id.default_code, inventory_id.location_id.name)
            inventory_id.action_start()
        res= inventory_id.get_apk_values()
        return res
    
    @api.model
    def set_to_delete(self,  values):
        inventory_id = self.browse(values['inventory_id'])
        inventory_id._set_to_delete(values['to_delete'])
        return True

    def _set_to_delete(self, to_delete = False):
        self.move_ids.serial_ids.write({'to_Delete': False})
        return True

    @api.model
    def load_inventory_list(self, values):
        domain = values.get('domain',False)
        if not domain:
         domain = [('name', 'ilike', 'APK'), ('state', '=', 'confirm')]
        inv_ids = self.search_read(domain, ['id', 'name'])
        res = []
        for inv in inv_ids:
            res.append({
                'id': inv['id'],
                'name': inv['name']
                })
        return res

    @api.model
    def reset_apk(self, values):
        id = values.get('id')
        inventory_id = self.env['stock.serial.inventory'].browse(id)
        inventory_id.line_ids.serial_ids.unlink()
        inventory_id.line_ids.unlink()
        if values.get('reset', True):
            inventory_id.action_start()
            res = inventory_id.get_apk_values()
        else:
            inventory_id.unlink()
            res = {}
        return res 

    @api.model
    def validate_apk(self, values):
        id = values.get('id')
        inventory_id = self.env['stock.serial.inventory'].browse(id)
        inventory_id.action_validate()
        return True

    @api.model
    def create_serial_async(self, values):
        inventory_id = self.browse(values['inventory_id'])
        line_id = inventory_id.line_ids
        domain = [('name', '=', values['name']), ('product_id', '=', line_id.product_id.id)]
        lot_id = self.env['stock.production.lot'].search(domain, limit=1)
        

        vals = {'name': values['name'], 'line_id': line_id.id, 'to_delete': False}
        if lot_id:
            vals['serial_id'] = lot_id.id
        serial = self.env['serial.line.wzd'].create(vals)
        res = {
                'id': serial.id,
                'serial_id': serial.serial_id and serial.serial_id.id or False,
                'name': serial.name,
                'to_delete': serial.to_delete
        }
        return res