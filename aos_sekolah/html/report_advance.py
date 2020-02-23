from odoo.tools.report import report_sxw
from odoo.api import Environment
from odoo import SUPERUSER_ID
from odoo.tools.translate import _
from odoo.addons.aos_report_webkit import webkit_report
from odoo.addons.aos_report_webkit.report_helper import WebKitHelper
from odoo.addons.aos_report_webkit.webkit_report import webkit_report_extender

class adv_report_webkit(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(adv_report_webkit, self).__init__(cr, uid, name, context=context)
        self.line_no = 0
        self.localcontext.update({
            #'convert':self.convert,
            #'blank_line':self.blank_line,
            'get_journal':self.get_journal,
            'get_advance':self.get_advance,
            'get_subtotal':self.get_subtotal,
        })
    
    def get_journal(self, data):
        env = Environment(self.cr, SUPERUSER_ID, {})
        journals = env['account.journal']
        journal_ids = []
        for journal in journals.browse(data['form'][0]['journal_ids']):
            journal_ids.append(journal)
        return journal_ids
    
    def get_advance(self, data, journal):
        env = Environment(self.cr, SUPERUSER_ID, {})
        vouchers = env['account.voucher']
        voucher_ids = []
        for voucher in vouchers.search([('date','>=',data['form'][0]['from_date']),('date','<=',data['form'][0]['to_date']),('journal_id','=',journal.id)]):
            voucher_ids.append(voucher)
        return voucher_ids
    
#     def convert(self, amount, cur=False):
#         amt_id = amount_to_text_id.amount_to_text(amount, 'id', cur)
#         return amt_id
#     
    def get_subtotal(self, get_advance):
        amount = 0
        for voucher in get_advance:
            amount += voucher.amount
        return amount
    
webkit_report.WebKitParser('report.webkit.advance.voucher','account.voucher', 
                       'aos_sekolah/html/uang_muka.html',
                       parser=adv_report_webkit)
