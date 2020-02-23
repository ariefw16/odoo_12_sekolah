# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import timedelta


class ResCompany(models.Model):
    _inherit = "res.company"

    #TODO check all the options/fields are in the views (settings + company form view)
    auto_graduate = fields.Boolean(string='Auto Graduate for All Active Students')
    auto_fiscalyear = fields.Boolean(string='Auto Generate School Year')
