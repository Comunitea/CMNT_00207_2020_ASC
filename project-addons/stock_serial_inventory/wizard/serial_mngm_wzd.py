# -*- coding: utf-8 -*-
# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class SerialMngmLineWzd(models.TransientModel):

    _name = "serial.mngt.line.wzd"

    wzd_id = fields.Many2one("serial.mngt.wzd", "Wizard")
    name = fields.Char('Name')

class SerialMngtWzd(models.TransientModel):

    _name = "serial.mngt.wzd"

    line_id = fields.Many2one('stock.serial.inventory.line')
    line_ids = fields.One2many('serial.mngt.line.wzd', "wzd_id", string="Serials")
    to_delete = fields.Boolean("To delete")
    act_mode = fields.Selection(
        selection=[('all', 'Actualizar existencias'), ('zero', 'Vaciar antes')], 
        default='all', 
        string="Modo", 
        help="* Si seleccionas la opción de actualizar, solo se verán afectados lo números ue ingreses aquí\n* Si seleccionas la opción de vaciar, se vaciar las existencias y se añadirán los números que pongas\nLa opción por defecto es 'Actualizar existencias'")
    location_id = fields.Many2one(related='line_id.location_id')
    product_id = fields.Many2one(related='line_id.product_id')

    @api.multi
    def action_add_names(self):
        return self.action_apply_names(False)
    @api.multi
    def action_del_names(self):
        return self.action_apply_names(True)

    def action_apply_names(self, to_delete):
        serial_ids = self.line_id.serial_ids
        serial_names = serial_ids.mapped('name')
        line_wzd_names=[]
        #line_ids = self.env['serial.mngt.line.wzd']
        
        for line_id in self.line_ids:
            if line_id.name in line_wzd_names:
                continue
            #line_ids |= line_id
            line_wzd_names += [line_id.name]

        if self.act_mode == 'zero':
            serial_ids.write({'to_delete': True})
        if to_delete:
            serial_ids.filtered(lambda x: x.name in line_wzd_names).write({'to_delete': True})
        else:
            ## Existentes
            serial_ids.filtered(lambda x: x.name in line_wzd_names).write({'to_delete': False})
            ## Para crear.
            serial_vals = {
                'line_id': self.line_id.id,
                'to_delete': False
            }
            for new_name in line_wzd_names:
                if new_name not in serial_names:
                    serial_vals['name'] = new_name
                    self.env['serial.line.wzd'].create(serial_vals)

            