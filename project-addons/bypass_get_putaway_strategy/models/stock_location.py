# -*- coding: utf-8 -*-
# © 2019 Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

class StockLocation(models.Model):
    _inherit = "stock.location"

    def get_putaway_strategy(self, product):
        " No le veo sentido al original pq sobreescribe lo que tu le has forzado. Entonces:"
        " Si pongo una ubicación determinada de tipo interno porque el sistema debe de cambiarla ?????"
        " Por lo tanto si no tiene hijos y es de tipo interno NO SE CAMBIA"
        if not self.child_ids and self.usage == 'internal':
            return self
        return super().get_putaway_strategy(product)
