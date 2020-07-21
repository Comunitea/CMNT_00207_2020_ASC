# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.crm.models import crm_stage

crm_stage.AVAILABLE_PRIORITIES = [
    ("0", "Very Low"),
    ("1", "Low"),
    ("2", "Medium"),
    ("3", "High"),
    ("4", "Very High"),
]

from . import models
