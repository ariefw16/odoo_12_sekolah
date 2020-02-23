# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Linto C T(<https://www.cybrosys.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api


class AdvanceVoucher(models.TransientModel):
    _name = 'print.advance.voucher'
    _description = 'wizard print advance voucher'

    from_date = fields.Date(string="Start Date", required=False)
    to_date = fields.Date(string="End Date", required=False)
    journal_ids = fields.Many2many('account.journal', string="Journal", domain=[('type','in',('cash','bank'))])
#     product_categ = fields.Many2many('product.category', string="Category")
#     interval = fields.Integer(string="Interval(days)", default=30, required=True)
    
    @api.multi
    def action_print(self):
        context = dict(self._context or {})
        datas = {'ids': self.ids}
        datas['model'] = 'print.advance.voucher'
        datas['form'] = self.read()
        return { 
            'type': 'ir.actions.report.xml', 
            'report_name': 'webkit.advance.voucher', 
            'report_type': 'webkit', 
            'datas': datas
        }
        
