# -*- coding: utf-8 -*-
import time
from datetime import date, datetime
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.modules import get_module_resource
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, image_colorize,\
    image_resize_image_big
from odoo.exceptions import except_orm, Warning as UserError


class SchoolPrevious(models.Model):
    ''' Defining a student previous school information '''
    _name = "school.previous"
    _description = "Student Previous School"

    partner_id = fields.Many2one('res.partner', 'Student')
    name = fields.Char('Name Previous School', required=True)
    registration_no = fields.Char('NIS', required=True)
    admission_date = fields.Date('Register Date')
    exit_date = fields.Date('Final Date')
    grade_id = fields.Many2one('school.grade', string='Grade')
    #course_id = fields.Many2one('standard.standard', 'Course', required=True)
    #add_sub = fields.One2many('academic.subject', 'add_sub_id', 'Add Subjects')
    
class GraduateHistory(models.Model):
    ''' Defining a student previous school information '''
    _name = "graduate.history"
    _description = "Student Previous School"
    _order = 'sequence'
    
    partner_id = fields.Many2one('res.partner', string='Student')
    name = fields.Char('Description', required=True)
    sequence = fields.Integer('Sequence')
    graduate_date = fields.Date('Graduation Date')
    year_id = fields.Many2one('school.year', string='Year')
    level_id = fields.Many2one('school.level', string='Level')
    grade_id = fields.Many2one('school.grade', string='Grade')
    grade_line_id = fields.Many2one('school.grade.line', 'Classroom')
    class_rank = fields.Integer('Class Rank',required=True, default=0)
    average_score = fields.Float('Average Score Class', group_operator='avg')
    count_student = fields.Integer('Count', default=1)
    state = fields.Selection([('draft', 'Not Active'),
                              ('active', 'Active'),
                              ('alumni', 'Alumni'),                              
                              ('terminate', 'Terminate'),
                              ('update','On Update'),
                              ('cancel', 'Cancelled')],
                             'Status', readonly=True, store=True, related='partner_id.state')
    
class ResFamily(models.Model):
    ''' Defining a student emergency contact information '''
    _name = "res.family"
    _description = "Student Family Contact"

    partner_id = fields.Many2one('res.partner', 'Student')
    name = fields.Char('Family Name')
    relation = fields.Selection([('father', 'Father'),
             ('mother', 'Mother'),
             ('brosis','Brother/Sister'),                                 
             ('cousin','Cousin'),
             ('lain','Other'),], 'Relationship',)
    phone = fields.Char('Phone/Mobile', required=False)
    email = fields.Char('Email')