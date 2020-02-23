# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.modules import get_module_resource
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, image_colorize,\
    image_resize_image_big
from odoo.exceptions import except_orm, Warning as UserError

class SchoolYear(models.Model):
    ''' Defines an academic year '''
    _name = "school.year"
    _description = "School Year"
    
    #sequence = fields.Integer('Sequence', required=True, help="Sequence order you want to see this year.")
    name = fields.Char('Name Year', size=4, required=True, default=lambda self: time.strftime('%Y'), help='Name of academic year')
    code = fields.Char('Code', required=True, default=lambda self: 'TA' + str(time.strftime('%Y')), help='Code of academic year')
    date_start = fields.Date('Start Date', required=True, default=lambda self: time.strftime('%Y-07-01'), help='Starting date of academic year')
    date_stop = fields.Date('End Date', required=True, default=lambda self: datetime.strptime(time.strftime('%Y-07-01'), "%Y-%m-%d") + relativedelta(years=1, days=-1), help='Ending of academic year')
    month_ids = fields.One2many('school.month', 'year_id', 'Months',  help="related Academic months")
    #company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    description = fields.Text('Description')
           
    @api.model
    def _check_duration(self):
        if self.date_stop < self.date_start:
            return False
        return True
    
    @api.model
    def _valid_year(self):
        if self.name and self.name.isdigit():
            if int(self.name) >= 2016:
                return self.name
  
    _constraints = [
        (_check_duration, 'Error!\nThe start date of a fiscal year must precede its end date.', ['date_start','date_stop']),
        (_valid_year, 'Name Year is not valid', ['name'])
    ]
    
    @api.multi
    def unlink(self):
        if self.env['res.partner'].search([('year_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot do that on a school year that contains students.'))
        return super(SchoolGradeLine, self).unlink()
    
    @api.onchange('name')
    def _onchange_name(self):
        if not self.name:
            return
        self.code = 'TA'+self.name
        self.date_start = datetime.strptime(time.strftime(self.name+'-07-01'), "%Y-%m-%d")
        self.date_stop = datetime.strptime(time.strftime(self.name+'-07-01'), "%Y-%m-%d") + relativedelta(years=1, days=-1)
 
    @api.onchange('date_start')
    def _onchange_date_start(self):
        if not self.date_start:
            return
        if self.date_start:
            self.date_stop = datetime.strptime(time.strftime(self.date_start), "%Y-%m-%d") + relativedelta(years=1, days=-1)
        
#     @api.onchange('date_stop')
#     def _onchange_date_stop(self):
#         if not self.date_stop:
#             return
#         if self.date_stop:
#             self.date_start = datetime.strptime(time.strftime(self.date_stop), "%Y-%m-%d") + relativedelta(years=-1, days=1)
    @api.multi
    def _cron_create_school_year(self):
        year_ids = self.env['school.year'].search([], limit=1, order='name desc')
        school_config_ids = self.env['school.config.settings'].search([], limit=1, order='id desc')
        if year_ids and school_config_ids.auto_fiscalyear:
            name_year = str(int(year_ids.name)+1)
            vals = {
                'name': name_year,
                'code': 'TA'+name_year,
                'date_start': datetime.strptime(time.strftime(name_year+'-07-01'), "%Y-%m-%d"),
                'date_stop': datetime.strptime(time.strftime(name_year+'-07-01'), "%Y-%m-%d") + relativedelta(years=1, days=-1),
                'description': 'Generate Automatic by System'
                #'company_id': self.company_id.id,
            }
            #print "====_cron_create_school_year====",vals
            return self.create(vals)
        
    def generate_period(self):
        period_obj = self.env['school.month']
        for fy in self:
            fy.month_ids.unlink()
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
            i = 1
            while ds.strftime('%Y-%m-%d') < fy.date_stop:
                de = ds + relativedelta(months=6, days=-1)

                if de.strftime('%Y-%m-%d') > fy.date_stop:
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')
                #print "====i=====",i
                period_obj.create({
                    'name': '0'+str(i)+ds.strftime('/%Y'),
                    'code': '0'+str(i)+ds.strftime('/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'year_id': fy.id,
                })
                i+=1
                ds = ds + relativedelta(months=6)
        return True

class SchoolMonth(models.Model):
    ''' Defining a month of an academic year '''
    _name = "school.month"
    _description = "School Month"
    _order = "date_start"

    name = fields.Char('Period', required=True, help='Name of Academic month')
    code = fields.Char('Code', required=True, help='Code of Academic month')
    date_start = fields.Date('Start Date', required=True, help='Starting of academic month')
    date_stop = fields.Date('End Date', required=True, help='Ending of academic month')
    year_id = fields.Many2one('school.year', 'Year', required=True, help="Related academic year ")
    description = fields.Text('Description')
    
    @api.multi
    def unlink(self):
        if self and self.env['res.partner'].search([('month_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot do that on a month that contains students.'))
        return super(SchoolMonth, self).unlink()

#     @api.constrains('date_start', 'date_stop')
#     def _check_duration(self):
#         if (self.date_stop and self.date_start and self.date_stop <
#                 self.date_start):
#             raise UserError(_('Error ! The duration of the Month(s)\ is/are invalid.'))