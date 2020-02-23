# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api

class StudentReport(models.Model):
    _name = "student.report"
    _description = "Student Report"
    _auto = False

    date = fields.Date(readonly=True)
    year_id = fields.Many2one('school.year', string='Year', readonly=True)
    level_id = fields.Many2one('school.level', string='Level', readonly=True)
    grade_id = fields.Many2one('school.grade', string='Grade', readonly=True)
    grade_line_id = fields.Many2one('school.grade.line', string='Classroom', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Student', readonly=True)
    count_student = fields.Float(string='Total', readonly=True)
    state = fields.Selection([('draft', 'Not Active'),
                              ('active', 'Active'),
                              ('alumni', 'Alumni'),                              
                              ('terminate', 'Terminate'),
                              ('update','On Update'),
                              ('cancel', 'Cancelled')], string='Status', readonly=True)

    _order = 'date desc'

    _depends = {
        'res.partner': [
            'name', 'admission_date', 'year_id', 'level_id', 'grade_id', 'grade_line_id'
        ],
    }

    def _select(self):
        select_str = """
            SELECT sub.id, sub.name, sub.date, sub.year_id, 
                sub.level_id, sub.grade_id, sub.grade_line_id, sub.state, sub.count_student
        """
        return select_str

    def _sub_select(self):
        select_str = """
                SELECT ail.id AS id,
                    ail.admission_date AS date,
                    ail.name,
                    ail.year_id, ail.level_id, ail.grade_id, ail.grade_line_id,
                    ail.state, COUNT(ail.id) AS count_student
        """
        return select_str

    def _from(self):
        from_str = """
                FROM res_partner ail
                WHERE is_student = True and year_id is not null
                 and level_id is not null and grade_id is not null and grade_line_id is not null
        """
        return from_str

    def _group_by(self):
        group_by_str = """
                GROUP BY ail.id, ail.name, ail.admission_date, ail.year_id, 
                    ail.level_id, ail.grade_id, ail.grade_line_id, ail.state
        """
        return group_by_str

    @api.model_cr
    def init(self):
        # self._table = account_invoice_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM (
                %s %s %s
            ) AS sub
        )""" % (self._table,
            self._select(), self._sub_select(), self._from(), self._group_by()))
