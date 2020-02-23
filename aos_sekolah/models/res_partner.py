# -*- coding: utf-8 -*-
import time
from datetime import date, datetime
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.modules import get_module_resource
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, image_colorize,\
    image_resize_image_big
from odoo.exceptions import except_orm, Warning as UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    is_advance = fields.Boolean('Is Advance', default=lambda self: self._context.get('is_advance', False))

class ResPartner(models.Model):
    ''' Defining a student information '''
    _inherit = 'res.partner'
    #_inherit = ['mail.thread', 'ir.needaction_mixin']

    @api.multi
    @api.depends('date_of_birth')
    def _calc_age(self):
        for partner in self:
            if partner.date_of_birth:
                start = datetime.strptime(partner.date_of_birth, DEFAULT_SERVER_DATE_FORMAT)
                end = datetime.strptime(time.strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT)
                partner.update({
                    'age': ((end - start).days / 365),
                })
                
    
    @api.multi
    @api.depends('graduate_lines')
    def _compute_average_score(self):
        total_score = line_len = 0        
        for partner in self:
            total_score = sum(line.average_score for line in partner.graduate_lines)
            for graduate in partner.graduate_lines:
                line_len += 1
            if line_len:
                partner.update({
                    'total_average_score': total_score / line_len,
                })
        
    is_current = fields.Boolean(string='Current Active', default=lambda self: self._context.get('is_current', False))
    is_student = fields.Boolean(string='Is Student?', default=lambda self: self._context.get('is_student', False),
        help="Check if the contact is a Student, otherwise it is a person")
    is_teacher = fields.Boolean(string='Is Teacher?', default=lambda self: self._context.get('is_guru', False),
        help="Check if the contact is a Teacher, otherwise it is a person")
    student_type = fields.Selection(string='Student Type',
        selection=[('person', 'Grade'), ('company', 'Student')],
        compute='_compute_student_type', readonly=False)
    reg_code = fields.Char('Registration Number', help='Code Registration Number Student', 
                    default=lambda obj: obj.env['ir.sequence'].next_by_code('student.registration'))
    student_code = fields.Char('Code Student')
    nis = fields.Char('Nomor Induk Siswa')
    year_id = fields.Many2one('school.year', 'School Year')
    level_id = fields.Many2one('school.level', 'Level')
    grade_id = fields.Many2one('school.grade', 'Grade')
    grade_line_id = fields.Many2one('school.grade.line', 'Classroom')
    roll_no = fields.Integer('Roll No.', readonly=True)
    admission_date = fields.Date('Register Date')
    date_start = fields.Date('Start Enter Date')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender', required=True, states={'done': [('readonly', True)]})
    place_of_birth = fields.Char('Place of Birth')
    date_of_birth = fields.Date('Date of Birth', states={'done': [('readonly', True)]})
    age = fields.Integer('Age (year)', compute='_calc_age', readonly=True)
    blood_group = fields.Char('Blood Type')
    height = fields.Float('Height')
    weight = fields.Float('Weight')
    emergency_contact = fields.Char('Emergency Contact')
    emergency_phone = fields.Char('Emergency Contact Phone')
    contact_info = fields.Selection([('father', 'Father'),
             ('mother', 'Mother'),
             ('brosis','Brother/Sister'),                                 
             ('cousin','Cousin'),
             ('lain','Other'),], 'Emergency Contact Relation')
    parent_lines = fields.Many2many('res.partner', 'orang_tua_wali_rel', 'partner_id', 'parent_id', 'Parents')
    remark = fields.Text('Notes')
    religion = fields.Selection([('islam', 'Islam'),
                                  ('kristen', 'Kristen'),
                                  ('katholik', 'Katholik'),                                  
                                  ('budha', 'Budha'),                                  
                                  ('hindu', 'Hindu'),
                                  ('konghucu', 'Konghucu')],
                             'Agama')
    type_student = fields.Selection([('new', 'New Student'),
                                  ('move', 'Transfer Student'),
                                  ('aksel', 'Acceleration Student')],
                             'Student Type', default='new')
    state_id = fields.Many2one("res.country.state", string='Province', ondelete='restrict')
    state = fields.Selection([('draft', 'Not Active'),
                              ('confirm', 'Confirm'),
                              ('validate','Validate'),
                              ('reject','Rejected'),
                              ('active', 'Active'),
                              ('alumni', 'Graduate'),                              
                              ('terminate', 'Terminate'),
                              ('leave','Leave'),
                              ('update','On Update'),
                              ('cancel', 'Cancelled')],
                             'Status', track_visibility='onchange', copy=False, default='draft')
    
    total_average_score = fields.Float(string='Average Score', readonly=True, compute='_compute_average_score')
    
    graduate_lines = fields.One2many('graduate.history', 'partner_id', 'Graduation Histories')
    school_lines = fields.One2many('school.previous', 'partner_id', 'School Histories')
    family_lines = fields.One2many('res.family', 'partner_id', 'Families')
    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Payable", oldname="property_account_payable",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=False)
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable", oldname="property_account_receivable",
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=False)
    
    _sql_constraints = [('nis_partner_unique', 'unique(nis)', 'Nomor Induk Siswa (NIK) harus unik!')]
    
    @api.multi
    @api.depends('invoice_ids')
    def name_get(self):
        context = self._context or {}
        result = []
        move_line = self.env['account.move.line']
        partner_ids = []
        for partner in self:
            #print "====is_school====",partner.name,partner.supplier
            if context.get('is_school') and context.get('account_id'):
                move_line_ids = False
                if context.get('is_student'):
                    move_line_ids = move_line.search([('partner_id','=',partner.id),('account_id','=',context.get('account_id')),('reconciled','=',False),('partner_id.is_student','=',context.get('is_student'))])
                    #print "==move_line_ids===1111",move_line_ids,context.get('is_student')
                if not move_line_ids and context.get('is_customer'):
                    move_line_ids = move_line.search([('partner_id','=',partner.id),('account_id','=',context.get('account_id')),('reconciled','=',False),('partner_id.customer','=',context.get('is_customer'))])
                    #print "==move_line_ids===2222",move_line_ids,context.get('is_customer')
                if not move_line_ids and context.get('is_supplier'):
                    move_line_ids = move_line.search([('partner_id','=',partner.id),('account_id','=',context.get('account_id')),('reconciled','=',False),('partner_id.supplier','=',context.get('is_supplier'))])
                    #print "==move_line_ids===3333",move_line_ids,context.get('supplier')
                if move_line_ids:
                    if partner.nis:
                        name = partner.name + ' ['+partner.nis+']'
                    elif partner.reg_code:
                        name = partner.name + ' ['+partner.reg_code+']'
                    else:
                        name = partner.name
                    result.append((partner.id, name))
                else:
                    partner_ids = False
                    if context.get('is_student'):
                        partner_ids = self.search([('is_student','=',context.get('is_student'))])
                    if not partner_ids and context.get('is_customer'):
                        partner_ids = self.search([('customer','=',context.get('is_customer'))])
                    if not partner_ids and context.get('is_supplier'):
                        partner_ids = self.search([('supplier','=',context.get('is_supplier'))])
                        # print "--move_line_ids--",partner_ids,context.get('is_supplier')
#                     if partner_ids:
#                         if partner.nis:
#                             name = partner.name + ' ['+partner.nis+']'
#                         elif partner.reg_code:
#                             name = partner.name + ' ['+partner.reg_code+']'
#                         else:
#                             name = partner.name
#                         result.append((partner.id, name))
            else:
                result.append((partner.id, partner.name))
        #print "===partner_ids===",partner_ids
        if partner_ids:
            for part in partner_ids:
                if part.nis:
                    name = part.name + ' ['+part.nis+']'
                elif not part.supplier and not part.customer and partner.reg_code:
                    name = part.name + ' ['+part.reg_code+']'
                else:
                    name = part.name
                result.append((part.id, name))
        return result
    
    def open_student_fee_history(self):
        '''
        This function returns an action that display invoices/refunds made for the given partners.
        '''
        action = self.env.ref('aos_sekolah.action_fee_register_form')
        result = action.read()[0]
        result['domain'] = [('partner_id', 'in', self.ids)]
        return result
    
    @api.depends('is_student')
    def _compute_student_type(self):
        for partner in self:
            partner.student_type = 'company' if partner.is_student else 'person'

    @api.multi
    def set_to_cancel(self):
        return self.write({'state': 'cancel'})
    
    @api.multi
    def set_confirm(self):
        return self.write({'state': 'confirm'})
    
    @api.multi
    def set_to_update(self):
        return self.write({'state': 'update'})
    
    @api.multi
    def set_to_leave(self):
        return self.write({'state': 'leave'})
    
    @api.multi
    def set_to_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def set_active(self):
        if not self.nis:
            raise UserError(_('You must complete field "Nomor Induk Siswa" Student!'))
        if not self.date_start:
            raise UserError(_('You must complete field "Start Date" Student!'))
        if not self.grade_line_id:
            raise UserError(_('You must complete field "Classroom" Student!'))
        if self.fee_line and not all(line.date_next for line in self.fee_line):
            raise UserError(_('You must complete field "Date to Invoice" on Student Fee!'))
        return self.write({'state': 'active'})
    
    @api.multi
    def set_alumni(self):
        return self.write({'state': 'alumni'})

    @api.multi
    def set_terminate(self):        
        return self.write({'state': 'terminate'})

    @api.multi
    def set_done(self):        
        return self.write({'state': 'done'})
    
    @api.multi
    def grade_set_up(self):
        grade_obj = self.env['school.grade']
        if self.grade_id:
            grade_next = grade_obj.search([('sequence','=',self.grade_id.sequence+1)])
            if grade_next:
                self.write({'grade_id': grade_next.id, 'grade_line_id': False})
        else:
            grade_first = grade_obj.search([('sequence','=',1)])
            if grade_first:
                self.write({'grade_id': grade_first.id, 'grade_line_id': False})
        return True
    
    @api.multi
    def _action_grade_next(self, automatic=False):
        context = dict(self._context or {})
        year_obj = self.env['school.year']
        level_obj = self.env['school.level']
        grade_obj = self.env['school.grade']
        grade_line_obj = self.env['school.grade.line']
        partner_obj = self.env['res.partner']
        current_date = fields.Date.today()
        level_max = level_obj.search([], limit=1, order='sequence desc')
        #grade_max = grade_obj.search([], limit=1, order='sequence desc')                
        if not automatic:
            #print "IF MANUAL"
            for part in self:
                graduate_sequence = int(len(self.env['graduate.history'].search([('partner_id','=',part.id)])))
                grade_max = grade_obj.search([('level_id','=',part.level_id.id)], limit=1, order='sequence desc')
                if part.grade_id.sequence < grade_max.sequence:
                    get_level_id = part.level_id.id
                    get_grade_id = grade_obj.search([('level_id','=',get_level_id),('sequence','=',part.grade_id.sequence + 1)], limit=1, order='sequence asc')
                    get_grade_line_id = grade_line_obj.search([('grade_id','=',get_grade_id.id),('sequence','=',part.grade_line_id.sequence)], limit=1, order='sequence asc')
                    vals = {'sequence': graduate_sequence,
                        'partner_id': part.id,
                        'name': part.grade_id.name + ' to ' + get_grade_id.name,
                        'year_id': part.year_id and part.year_id.id or False,
                        'level_id': get_level_id or False,
                        'grade_id': get_grade_id and get_grade_id.id or False,
                        'grade_line_id': get_grade_line_id and get_grade_line_id.id or False,
                        'graduate_date': part.year_id.date_stop,
                        'class_rank': 0,
                        'average_score': 0,
                        'count_student': 1,
                    }
                    graduate = self.env['graduate.history'].create(vals)
                    self.write({'level_id': get_level_id, 'grade_id': get_grade_id.id, 'grade_line_id': get_grade_line_id.id})
                elif part.grade_id.sequence == grade_max.sequence:
                    self.set_alumni()
        else:
            print("ELSE CRON",current_date)
            domain = [('id', 'in', self.ids)] if self.ids else [('level_id.autonextgrade','=',True),('state','=','active'),('year_id.date_stop', '<=', current_date)]
            partners = partner_obj.search(domain)
            #print "====partners====",domain,partners
            for part in partners:
                get_year_id = year_obj.search([('date_start','=',time.strftime('%Y-07-01'))], limit=1, order='date_start asc')
                #print "====get_year_id====",get_year_id
                graduate_sequence = int(len(self.env['graduate.history'].search([('year_id','!=',get_year_id.id),('partner_id','=',part.id)])))
                grade_max = grade_obj.search([('level_id','=',part.level_id.id)], limit=1, order='sequence desc')
                #print "====",part.grade_id.sequence,grade_max.sequence
                if part.grade_id.sequence < grade_max.sequence:
                    #get_level_id = part.level_id.id
                    get_grade_id = grade_obj.search([('level_id','=',part.level_id.id),('sequence','=',part.grade_id.sequence + 1)], limit=1, order='sequence asc')
                    get_grade_line_id = grade_line_obj.search([('grade_id','=',get_grade_id.id),('sequence','=',part.grade_line_id.sequence)], limit=1, order='sequence asc')
                    #print "==name==",part.name,part.grade_id,get_year_id
                    vals = {'sequence': graduate_sequence,
                        'partner_id': part.id,
                        'name': part.grade_id.name + ' to ' + get_grade_id.name,
                        'year_id': part.year_id and part.year_id.id or False,#get_year_id and get_year_id.id or False,#
                        'level_id': part.level_id and part.level_id.id,#get_level_id or False,
                        'grade_id': part.grade_id and part.grade_id.id or False,#get_grade_id and get_grade_id.id or False,
                        'grade_line_id': part.grade_line_id and part.grade_line_id.id or False,#get_grade_line_id and get_grade_line_id.id or False,
                        'graduate_date': part.year_id.date_stop,
                        'class_rank': 0,
                        'average_score': 0,
                        'count_student': 1,
                    }
                    graduate = self.env['graduate.history'].create(vals)
                    part.write({'year_id': get_year_id.id, 'level_id': part.level_id.id, 'grade_id': get_grade_id.id, 'grade_line_id': get_grade_line_id.id})
                elif part.grade_id.sequence == grade_max.sequence:
                    part.set_alumni()
        return
    
    @api.multi
    def action_invoice(self):
        """ INI UNTUK MANUAL GRADE NEXT"""
        return self._action_grade_next()
    
    @api.model
    def _cron_grade_end_of_year(self):
        """ INI UNTUK AUTOMATIC GRADE NEXT BY CRON"""
        return self._action_grade_next(automatic=True)
    
#     @api.multi
#     def admission_done(self):
#         school_standard_obj = self.env['school.standard']
#         for student_data in self:
#             if student_data.age <= 5:
#                 raise except_orm(_('Warning'),
#                                  _('The student is not eligible.'
#                                    'Age is not valid.'))
#             domain = [('standard_id', '=', student_data.standard_id.id)]
#             school_standard_search_ids = school_standard_obj.search(domain)
#             if not school_standard_search_ids:
#                 raise except_orm(_('Warning'),
#                                  _('The standard is not defined'
#                                    'in a school'))
#             student_search_ids = self.search(domain)
#             number = 1
#             if student_search_ids:
#                 self.write({'roll_no': number})
#                 number += 1
#             reg_code = self.env['ir.sequence'].next_by_code('student.registration')
#             registation_code = str(student_data.school_id.state_id.name)\
#                 + str('/') + str(student_data.school_id.city)\
#                 + str('/')\
#                 + str(student_data.school_id.name) + str('/')\
#                 + str(reg_code)
#             stu_code = self.env['ir.sequence'].next_by_code('student.code')
#             student_code = str(student_data.school_id.code) + str('/') + str(student_data.year.code) + str('/') + str(stu_code)
#         self.write({'state': 'done',
#                     'admission_date': time.strftime('%Y-%m-%d'),
#                     'student_code': student_code,
#                     'reg_code': registation_code})
        return True
# end of res_partner()
