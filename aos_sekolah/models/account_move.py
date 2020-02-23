# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from odoo import fields, models, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _description = "Account Move Line"
    
    department_id = fields.Many2one('hr.department', string='Department/Unit')