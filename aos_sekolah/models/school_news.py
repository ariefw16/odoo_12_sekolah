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

class SchoolNews(models.Model):
    _name = 'school.news'
    _description = 'School News'
    _rec_name = 'subject'

    subject = fields.Char('Subject', required=True, help='Subject of the news.')
    date = fields.Datetime('Expiry Date', help='Expiry date of the news.')
    description = fields.Text('Description', help="Description")
    user_ids = fields.Many2many('res.users', 'user_news_rel', 'id', 'user_ids', 'User News', help='Name to whom this news is related.')
    color = fields.Integer('Color Index', default=0)

    @api.multi
    def news_update(self):
        #emp_obj = self.env['hr.employee']
        obj_mail_server = self.env['ir.mail_server']
        mail_server_ids = obj_mail_server.search([])
        if not mail_server_ids:
            raise except_orm(_('Mail Error'),
                             _('No mail outgoing mail server'
                               'specified!'))
        mail_server_record = mail_server_ids[0]
        email_list = []
        for news in self:
            if news.user_ids:
                for user in news.user_ids:
                    if user.email:
                        email_list.append(user.email)
                if not email_list:
                    raise except_orm(_('User Email Configuration '),
                                     _("Email not found in users !"))
#             else:
#                 for employee in emp_obj.search([]):
#                     if employee.work_email:
#                         email_list.append(employee.work_email)
#                     elif employee.user_id and employee.user_id.email:
#                         email_list.append(employee.user_id.email)
#                 if not email_list:
#                     raise except_orm(_('Mail Error'), _("Email not defined!"))
            t = datetime.strptime(news.date, '%Y-%m-%d %H:%M:%S')
            body = 'Hi,<br/><br/> \
                    This is a news update from <b>%s</b>posted at %s<br/><br/>\
                    %s <br/><br/>\
                    Thank you.' % (self._cr.dbname,
                                   t.strftime('%d-%m-%Y %H:%M:%S'),
                                   news.description)
            smtp_user = mail_server_record.smtp_user
            notification = 'Notification for news update.'
            message = obj_mail_server.build_email(email_from=smtp_user,
                                                  email_to=email_list,
                                                  subject=notification,
                                                  body=body,
                                                  body_alternative=body,
                                                  email_cc=None,
                                                  email_bcc=None,
                                                  reply_to=smtp_user,
                                                  attachments=None,
                                                  references=None,
                                                  object_id=None,
                                                  subtype='html',
                                                  subtype_alternative=None,
                                                  headers=None)
            obj_mail_server.send_email(message=message, mail_server_id=mail_server_ids[0].id)
        return True