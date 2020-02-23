from odoo import fields, models, api, _
from odoo.exceptions import UserError

class GradeNextStudent(models.TransientModel):
    _name = "grade.next.student"
    _description = "Grade Next Upgrade"

    year_id = fields.Many2one('school.year', 'School Year')
    level_id = fields.Many2one('school.level', 'Level')
    grade_id = fields.Many2one('school.grade', 'Grade')
    grade_line_id = fields.Many2one('school.grade.line', 'Classroom')
    graduate_date = fields.Date('Graduation Date')
    class_rank = fields.Integer('Class Rank')
    average_score = fields.Float('Average Score')
    
    @api.multi
    def grade_next_move(self):
        context = dict(self._context or {})
        partners = self.env['res.partner'].search([('level_id.autonextgrade','=',True),('id','in',context.get('active_ids'))])
        for grade_next in self:
            for part in partners:
                graduate_sequence = int(len(self.env['graduate.history'].search([('partner_id','=',part.id)])))
                vals = {'sequence': graduate_sequence,
                        'partner_id': part.id,
                        'name': part.grade_id.name + ' to ' + grade_next.grade_id.name,
                        'year_id': part.year_id and part.year_id.id or False,
                        'level_id': part.level_id and part.level_id.id or False,
                        'grade_id': part.grade_id and part.grade_id.id or False,
                        'grade_line_id': part.grade_line_id and part.grade_line_id.id or False,
                        'graduate_date': grade_next.graduate_date,
                        'class_rank': grade_next.class_rank,
                        'average_score': grade_next.average_score,
                }
                graduate = self.env['graduate.history'].create(vals)
                part.write({'year_id': grade_next.year_id and grade_next.year_id.id or False,
                            'grade_id': grade_next.grade_id and grade_next.grade_id.id or False,
                            'grade_line_id': grade_next.grade_line_id and grade_next.grade_line_id.id or False,})
        return {'type': 'ir.actions.act_window_close'}
    
    #INI FUNGSI BUAT PARTNER BARU
#     @api.multi
#     def grade_next_move(self):
#         context = dict(self._context or {})
#         partners = self.env['res.partner'].browse(context.get('active_ids'))
#         for grade_next in self:
#             for part in partners:
#                 vals = {'parent_id': part.parent_id and part.parent_id or part.id,
#                         'name': grade_next.grade_id.name + '/' + grade_next.grade_line_id.name,
#                         'year_id': grade_next.year_id and grade_next.year_id.id or False,
#                         'grade_id': grade_next.grade_id and grade_next.grade_id.id or False,
#                         'grade_line_id': grade_next.grade_line_id and grade_next.grade_line_id.id or False,
#                         'is_current': True,
#                         'is_student': True,
#                         'customer': True,
#                         'student_type': 'person',
#                         'state': 'active',
#                         'reg_code': part.reg_code,
#                         'nis': part.nis,
#                         'admission_date': part.admission_date,
#                         'date_start': part.date_start,
#                         'gender': part.gender,
#                         'place_of_birth': part.place_of_birth,
#                         'date_of_birth': part.date_of_birth,
#                         'blood_group': part.blood_group,
#                         'emergency_contact': part.emergency_contact,
#                         'contact_info': part.contact_info,
#                         'parent_lines': [(6, 0, part.parent_lines.ids)],
#                         'remark': part.remark,
#                         'type_student': part.type_student,
#                         'state': part.state,
#                         'school_lines': [(6, 0, part.school_lines.ids)],
#                         'family_lines': [(6, 0, part.family_lines.ids)],
#                         'website': part.website,
#                         'comment': part.comment,
#                         'category_id': [(6, 0, part.category_id.ids)],
#                         'credit_limit': part.credit_limit,
#                         'barcode': part.barcode,
#                         'function': part.function,
#                         'street': part.street,
#                         'street2': part.street2,
#                         'zip': part.zip,
#                         'city': part.city,
#                         'state_id': part.state_id and part.state_id.id,
#                         'country_id': part.country_id and part.country_id.id,
#                         'email': part.email,
#                         'image': part.image,
#                         'image_medium': part.image_medium,
#                         'image_small': part.image_small,
#                 }
#                 new_partner = part.create(vals)
#                 part.write({'is_current': False})
#         return {'type': 'ir.actions.act_window_close'}
