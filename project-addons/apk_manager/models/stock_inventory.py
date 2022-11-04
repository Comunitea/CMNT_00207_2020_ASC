# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import unicodedata
# from odoo.tools.float_utils import float_compare
PRODUCT_VALUES= ['id', 'default_code', 'name', 'display_name']
LOCATION_VALUES = ['id', 'barcode', 'name', 'display_name', 'usage', 'parent_path']

"""
class StockInventoryTracking(models.Model):
    _inherit ="stock.inventory.tracking"

    @api.model
    def get_apk_values(self):
        product_id = {}
        location_id = {}
        if len(self) == 1:
            product_id = {}
            for item in PRODUCT_VALUES:
                product_id[item] = self.product_id[item]
            location_id = {}
            for item in LOCATION_VALUES:
                location_id[item] = self.location_id[item]
        res = {'id': self.id,
                'product_id': product_id,
                'tracking': self.product_id.template_tracking,
                'location_id': location_id,
                'prod_lot_id': {'id': self.prod_lot_id.id, 'name': self.prod_lot_id.display_name } if self.prod_lot_id else {},
                'to_delete': False,
                'lot_name': self.prod_lot_id.name}

        return res"""

class InventoryLine(models.Model):
    _inherit ="stock.inventory.line"


    @api.model
    def load_virtual_lot_ids(self, values):
        line = self.browse(values['id'])
        res = []
        for vl_id in line.virtual_lot_ids:
            res += [vl_id.name]
        res_string = ','.join(res)
        return {'list': res, 'string': res_string}

    @api.model
    def create_apk_prod_lot(self, values):

        name = values.get('lot_name')
        product_id = values.get('product_id')
        lot_values = {'name': name, 'ref': name, 'product_id': product_id}
        lot_id = self.env['stock.production.lot'].create(lot_values)
        line = self.browse(values.get('line_id'))
        line.prod_lot_id = lot_id
        return  {'id': lot_id.id, 'name': lot_id.display_name }


    def get_apk_values(self, id = False):
        ##LImito a 100 las lineas de inventario que muestro

        if not self:
            obj_line_ids = self
        else:
            ##line_ids = filter_lines(lines.sorted(key=lambda r: (r.location_id.removal_priority, r.write_date), reverse = True))
            lines = self.sorted(key=lambda x: (x.location_id.removal_priority, x.product_id.default_code))
            obj_line_ids = lines[0:100]
        line_ids = []

        dict_l_values = {}
        dict_p_values = {}

        for line in obj_line_ids:
            if not line.product_id.default_code in dict_p_values.keys():
                dict_p_values[line.product_id.default_code] = line.inventory_id.get_apk_product_ids({'id': line.product_id.id})[0]
            if not line.location_id.barcode in dict_l_values.keys():
                dict_l_values[line.location_id.barcode] = line.inventory_id.get_apk_location_ids({'id': line.location_id.id})[0]

            new_line = {'id': line.id,
                        'product_id': dict_p_values[line.product_id.default_code],
                        'tracking': line.product_id.template_tracking,
                        'location_id': dict_l_values[line.location_id.barcode],
                        'product_uom_id': {'id': line.product_uom_id.id, 'name': line.product_uom_id.display_name },
                        'theoretical_qty': line.theoretical_qty,
                        'prod_lot_id': {'id': line.prod_lot_id.id, 'name': line.prod_lot_id.display_name } if line.prod_lot_id else {},
                        'product_qty': line.product_qty,
                        'removal_priority': line.location_id.removal_priority,
                        'acl': False}
            line_ids += [new_line]
        return line_ids

    @api.model
    def write_apk_qties(self, values):
        line_id = values.get('id')
        Line = self.browse(line_id)
        product_qty = values.get('product_qty', 0)
        if not product_qty:
            product_qty = Line.product_qty + values.get('inc', 0)
        Line.product_qty = product_qty
        return Line.get_apk_values()

    @api.model
    def load_multi_serials(self, values):
        ##import ipdb; ipdb.set_trace()
        id = values.get('id', False)
        delete = values.get('delete', False)

        line_id = self.env['stock.inventory.line'].browse(id)
        if line_id:
            serial_names = values.get('serial_names', [])

        if delete:
            line_id.virtual_lot_ids.unlink()
            line_id.product_qty = len(line_id.virtual_lot_ids)
            serial_ids = self.env['stock.virtual.serial']
            names=[]
        if not serial_names:
            return line_id.get_apk_values()
        if not delete:
            domain = [
                ('product_id', '=', line_id.product_id.id),
                ('inventory_line_id', '=', line_id.id),
                ('inventory_id', '=', line_id.inventory_id.id),
                ('location_id', '=', line_id.location_id.id)
            ]
            serial_ids = self.env['stock.virtual.serial'].search(domain)
            names = serial_ids.mapped('name')

        res_ids = line_id
        for name_ in serial_names.split():
            name = name_.strip()
            if name in names:
                continue
            names += [name]
            serial_id = serial_ids.filtered(lambda x: x.name == name)
            if serial_id:
                inv_line = serial_id.inventory_line_id
                vals = {
                    'location_id': line_id.location_id.id,
                    'inventory_line_id': line_id.id,
                    'inventory_id': line_id.inventory_id.id,
                }
                serial_id.write(vals)
                inv_line.product_qty = len(inv_line.virtual_lot_ids)
                #res_ids |= inv_line
            else:
                vals = {'name': name,
                        'location_id': line_id.location_id.id,
                        'inventory_line_id': line_id.id,
                        'inventory_id': line_id.inventory_id.id,
                        'product_id': line_id.product_id.id,}
                serial_ids |= self.env['stock.virtual.serial'].create(vals)


        line_id.product_qty = len(line_id.virtual_lot_ids)
        return res_ids.get_apk_values()

class Inventory(models.Model):
    _inherit = "stock.inventory"

    @api.model
    def create_apk_line(self, values):
        lot_id = self.env['stock.production.lot']
        lot_name = values.get('lot_name', False)
        inventory_id = values.get('inventory_id')
        product_id = self.env['product.product'].browse(values['product_id'])
        inventory_id = self.browse(inventory_id)
        
        if product_id.tracking != 'none':
            res = {'WaitingNewLot': True}
            if values.get('lot_name', False):
                lot_domain = [('name', '=', lot_name), ('product_id', '=', values['product_id'])]
                lot_id = lot_id.search(lot_domain)
                if not lot_id:
                    lot_id = lot_id.create({'name': lot_name, 'product_id': values['product_id']})
                values.update(lot_id=lot_id.id)
        else:
            res = {'WaitingNewLot': False}
        model = 'stock.inventory.line'
        new_line = self.env[model].new(values)
        new_line._onchange_product()
        new_line._onchange_quantity_context()
        new_line_id = self.env[model].create(new_line._convert_to_write(new_line._cache))

        lines = inventory_id.get_apk_line_values()
        res.update({
            'line_ids': lines,
            'line_selected': inventory_id.get_apk_line_values(line_id=new_line_id.id)})

        return res

    @api.model
    def delete_apk_line(self, values):
        id = values.get('id')
        model = values.get('model')
        self.env[model].browse(id).unlink()
        return True


    @api.model
    def write_apk_qties(self, values):
        line_id = values.get('id')
        model = values.get('model')
        Line = self.env[model].browse(line_id)
        product_qty = values.get('product_qty', 0)
        if not product_qty:
            product_qty = Line.product_qty + values.get('inc', 0)
        Line.product_qty = product_qty

        return Line.get_apk_values()

    @api.model
    def get_apk_product_ids(self, values={}):
        search = values.get('search', '')
        p_id = values.get('id', 0)
        domain = values.get('domain', [])
        limit = values.get('limit', 20)
        inventory_id = values.get('inventory_id', 0)

        if not domain:
            if p_id:
                domain = [('id', '=', p_id)]
            if search:
                domain = ['|', ('name', 'ilike', search), ('default_code', 'ilike', search)]
                limit = 50
            if inventory_id:
                inventory_id = self.browse(inventory_id)
                if inventory_id.product_id:
                    domain = [('id', '=', inventory_id.product_id.id)]
                else:
                    if not domain:
                        p_ids = inventory_id.line_ids.mapped('product_id') ## | inventory_id.available_lot_ids.mapped('product_id')
                        limit = 75
                        domain = [('id', 'in', p_ids.ids)]
        else:
            domain = []
            limit = 25
        product_ids = self.env['product.product'].search_read(domain=domain, fields=PRODUCT_VALUES, limit=limit)#, limit=limit)
        for product in product_ids:
            product['name'] = unicodedata.normalize("NFKD",product['name'])
        if len(product_ids) > 1:
            product_ids += [{'id': 0, 'default_code': 'Todos', 'name': 'Todos'}]
        return product_ids

    @api.model
    def get_apk_location_ids(self, values):
        ## Texto de Búsqueda
        search = values.get('search', '')
        location_id = values.get('id', 0)
        domain = values.get('domain', [])

        inventory_id = values.get('inventory_id', 0)
        ## Si envío un id, devulevo ese id
        if location_id:
            domain = [('id', 'child_of', location_id)]

        ## Si veiene un inventario, devulevo los hijos de ese inventario
        elif inventory_id:
            domain = [('id', '=', inventory_id)]
            l_id = self.env['stock.inventory'].search_read(domain, ['location_id'])[0]['location_id'][0]
            domain = [('id', 'child_of', l_id)]
        ## Si viene un texto de búsqueda lo añado al domain
        if search:
            domain += ['|', ('barcode', 'ilike', search), ('name', 'ilike', search)]

        ## Añado get_select al context para recuperar el codigo de barras en el nombre
        ctx = self._context.copy()
        ctx.update(get_select=True)
        ## Si llego sin dominio, devuelvo la ubnicación de stock (Solo debería pasar en generíca)
        if not domain:
            stock_location = self.env.ref('stock.stock_location_stock')
            domain = [('id', 'child_of', stock_location.id), ('usage', '=', 'view')]

        location_ids = self.env['stock.location'].with_context(ctx).search_read(domain, LOCATION_VALUES)
        #if not location_ids:
        #    raise ValidationError ('No encuentro ubicación')
        # if len(location_ids) > 1:
        #    location_ids += [{'id': 0, 'barcode': 'Todos', 'name': 'Todos', 'display_name': 'Todas'}]
        return location_ids

    @api.model
    def load_apk_inventory(self, values):
        id = values.get('id', False)

        if id and id > 0:
            inventory_id = self.browse(id)
        else:
            domain = [('state', '=', 'confirm'),
                      ('create_uid', '=', self.env.user.id),
                      ('filter', 'in', ['none', 'product'])]
            if id < 0:
                domain += [('id', '!=', -id)]
            inventory_id = self.search(domain, limit = 1)
        if not inventory_id:
            return False
        return inventory_id.get_apk_values()

    @api.model
    def new_apk_inventory(self, values):
        product_id = values.get('product_id', 0)
        location_id = values.get('location_id', 0)
        if product_id:
            filter1='product'
        else:
            filter1='none'
        values.update(filter=filter1)
        inventory_id = self.create(values)
        inventory_id.action_start()
        if not inventory_id.line_ids:
            if product_id and location_id:
                self.line_ids.create({
                    'inventory_id': inventory_id.id,
                    'product_id': product_id,
                    'location_id': location_id
                })
        return inventory_id.get_apk_values()

    def load_inventory_list(self, values):
        domain = values.get('domain', [('state', '=', 'confirm')])
        inv_ids = self.search_read(domain, ['id', 'name'])
        res = []
        for inv in inv_ids:
            res.append({
                'id': inv['id'],
                'name': inv['name']
                })
        return res

    def get_apk_line_values(self, line_id=False):
        ##LImito a 100 las lineas de inventario que muestro

        if line_id:
            obj_line_ids = self.line_ids.filtered(lambda x:x.id == line_id)
        else:

            ##line_ids = filter_lines(lines.sorted(key=lambda r: (r.location_id.removal_priority, r.write_date), reverse = True))
            lines = self.line_ids.sorted(key=lambda x: (x.location_id.removal_priority, x.product_id.default_code))
            obj_line_ids = lines[0:100]
        line_ids = []
        """
        location_ids = obj_line_ids.mapped('location_id')
        product_ids = obj_line_ids.mapped('product_id')

        domain = [('id', 'in', product_ids.ids)]
        list_p_values = self.get_apk_product_ids({'domain': domain, 'limit': 1000})['product_ids']
        dict_p_values = {}
        for p_value in list_p_values:
            dict_p_values[p_value['default_code']] = p_value

        domain = [('id', 'in', location_ids.ids)]
        list_l_values = self.get_apk_location_ids({'domain': domain})['location_ids']
        dict_l_values = {}
        for l_value in list_l_values:
            dict_l_values[l_value['barcode']] = l_value
        """
        dict_l_values = {}
        dict_p_values = {}
        for line in obj_line_ids:
            if not line.product_id.default_code in dict_p_values.keys():
                dict_p_values[line.product_id.default_code] = self.get_apk_product_ids({'id': line.product_id.id})[0]
            if not line.location_id.barcode in dict_l_values.keys():
                dict_l_values[line.location_id.barcode] = self.get_apk_location_ids({'id': line.location_id.id})[0]

            new_line = {'id': line.id,
                        'product_id': dict_p_values[line.product_id.default_code],
                        'tracking': line.product_id.template_tracking,
                        'location_id': dict_l_values[line.location_id.barcode],
                        'product_uom_id': {'id': line.product_uom_id.id, 'name': line.product_uom_id.display_name },
                        'theoretical_qty': line.theoretical_qty,
                        'prod_lot_id': {'id': line.prod_lot_id.id, 'name': line.prod_lot_id.display_name } if line.prod_lot_id else False,
                        'product_qty': line.product_qty}
            line_ids += [new_line]
        return line_ids

    def get_apk_values(self):
        if not self:
            return False
        values = {  'id': self.id,
                    'name': self.name,
                    #'inventory_type': self.inventory_type,
                    'filter': self.filter,
                    }
        if self.filter == 'none':
            values['product_id'] = {}
        else:
            values['product_id'] = self.get_apk_product_ids({'id': self.product_id.id})[0]
        values['location_id'] =self.get_apk_location_ids({'id': self.location_id.id})[0]
        values['line_ids'] = self.line_ids.get_apk_values()
        return values

    @api.model
    def action_validate_apk(self, values):
        inventory_id = self.browse(values['id'])
        inventory_id.action_validate()
        return True
