# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from datetime import date, datetime
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.modules import get_module_resource
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, image_colorize,\
    image_resize_image_big
from odoo.exceptions import except_orm, Warning as UserError

class SchoolLevel(models.Model):
    _name = 'school.level'
    _description = 'Level'
    
    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True)
    autonextgrade = fields.Boolean('Auto Next Grade')
    grade_ids = fields.One2many('school.grade', 'level_id', 'Grade')
    
    _sql_constraints = [('sequence_unique', 'unique(sequence)', 'sequence level must be unique!')]
    
    @api.multi
    def unlink(self):
        if self.env['res.partner'].search([('level_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot do that on a level that contains students.'))
        return super(SchoolLevel, self).unlink()
    
class SchoolGrade(models.Model):
    _name = 'school.grade'
    _description = 'Grade'
    
    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True)
    level_id = fields.Many2one("school.level", 'Level')
    grade_line_ids = fields.One2many('school.grade.line', 'grade_id', 'Classroom')
    
    _sql_constraints = [('sequence_level_id_unique', 'unique(level_id, sequence)', 'sequence grade must be unique!')]
    
    @api.multi
    def unlink(self):
        if self.env['res.partner'].search([('grade_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot do that on a grade that contains students.'))
        return super(SchoolGrade, self).unlink()

class SchoolGradeLine(models.Model):
    _name = 'school.grade.line'
    _description = 'Class'
    
    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True)
    #level_id = fields.Many2one("school.level", related='grade_id.level_id', string='Level')
    grade_id = fields.Many2one("school.grade", 'Grade')
    total_student = fields.Integer('Total Students', required=False)
    
    _sql_constraints = [('sequence_grade_id_unique', 'unique(grade_id, sequence)', 'sequence classroom must be unique!')]
    
    @api.multi
    def unlink(self):
        if self.env['res.partner'].search([('grade_line_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot do that on a classroom that contains students.'))
        return super(SchoolGradeLine, self).unlink()