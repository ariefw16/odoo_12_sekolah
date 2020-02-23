# -*- coding: utf-8 -*-
import time

from odoo.osv import expression
from datetime import date, datetime
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.modules import get_module_resource
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, image_colorize,\
    image_resize_image_big
from odoo.exceptions import except_orm, Warning as UserError

    
class AccountJournal(models.Model):
    ''' Defining a student information '''
    _inherit = "account.journal"

    show_on_dashboard = fields.Boolean(string='Show journal on dashboard', help="Whether this journal should be displayed on the dashboard or not", default=False)
    type = fields.Selection(default="general")
    general_debit_account_ids = fields.Many2many('account.account', 'account_journal_debit_ids_rel', 'journal_id', 'account_id', string='Default Debit Account',
        domain=[('deprecated', '=', False)], help="It acts as a default account for debit amount")
    general_credit_account_ids = fields.Many2many('account.account', 'account_journal_credit_ids_rel', 'journal_id', 'account_id', string='Default Credit Account',
        domain=[('deprecated', '=', False)], help="It acts as a default account for credit amount")
    debit_student = fields.Boolean('Student(db)')
    credit_student = fields.Boolean('Student(cr)')
    debit_customer = fields.Boolean('Customer(db)')
    credit_customer = fields.Boolean('Customer(cr)')
    debit_supplier = fields.Boolean('Supplier(db)')
    credit_supplier = fields.Boolean('Supplier(cr)')
    debit_product = fields.Boolean('Product(db)')
    credit_product = fields.Boolean('Product(cr)')
    debit_invoice = fields.Boolean('Transaction(db)')
    credit_invoice = fields.Boolean('Transaction(cr)')
    is_debit_reconcile = fields.Boolean('Reconcile(db)')
    is_credit_reconcile = fields.Boolean('Reconcile(cr)')
    
    @api.onchange('general_debit_account_ids')
    def onchange_general_debit_account_ids(self):
        if not self.general_debit_account_ids:
            return
        check_reconcile = False
        for account in self.general_debit_account_ids:
            check_reconcile = account.reconcile
        self.is_debit_reconcile = check_reconcile
        
    @api.onchange('general_credit_account_ids')
    def onchange_general_credit_account_ids(self):
        if not self.general_credit_account_ids:
            return
        check_reconcile = False
        for account in self.general_credit_account_ids:
            check_reconcile = account.reconcile
        self.is_credit_reconcile = check_reconcile

    @api.onchange('debit_invoice')
    def onchange_debit_invoice(self):
        if not self.debit_invoice:
            self.is_debit_reconcile = False

    @api.onchange('credit_invoice')
    def onchange_credit_invoice(self):
        if not self.credit_invoice:
            self.is_credit_reconcile = False
        
class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = "Account Move General"
    
    is_general = fields.Boolean('Is General', default=lambda self: self._context.get('is_general', False))
    is_debit_student = fields.Boolean('Is Student db', related='journal_id.debit_student')
    is_credit_student = fields.Boolean('Is Student cr', related='journal_id.credit_student')
    is_debit_customer = fields.Boolean('Is Customer db', related='journal_id.debit_customer')
    is_credit_customer = fields.Boolean('Is Customer cr', related='journal_id.credit_customer')
    is_debit_supplier = fields.Boolean('Is Supplier db', related='journal_id.debit_supplier')
    is_credit_supplier = fields.Boolean('Is Supplier cr', related='journal_id.credit_supplier')
    general_debit_account_ids = fields.Many2many('account.account', 'account_move_general_debit_ids_rel', 'move_id', 'account_id', string='Default Debit Account',
        domain=[('deprecated', '=', False)], help="It acts as a default account for debit amount")
    general_credit_account_ids = fields.Many2many('account.account', 'account_move_general_credit_ids_rel', 'move_id', 'account_id', string='Default Credit Account',
        domain=[('deprecated', '=', False)], help="It acts as a default account for credit amount")
    
#     @api.onchange('is_general')
#     def onchange_is_general(self):
#         return self.env['account.move.line'].fields_get(allfields=None, attributes=None)
    
    @api.onchange('journal_id')
    def onchange_general_journal_id(self):
        if not self.journal_id:
            return
        debit_accs = []
        credit_accs = []
        for acc_debit in self.journal_id.general_debit_account_ids:
            debit_accs.append(acc_debit.id)
        for acc_credit in self.journal_id.general_credit_account_ids:
            credit_accs.append(acc_credit.id)
        self.general_debit_account_ids = debit_accs
        self.general_credit_account_ids = credit_accs
        self.line_ids = []
        
    @api.multi
    def post(self):
        for move in self:
            for line in move.line_ids:
                if line.partner_id == line.move_line_id.partner_id and line.account_id == line.move_line_id.account_id and line.account_id.reconcile and not line.reconciled:
                    move.register_reconcile(line, line.move_line_id)
        return super(AccountMove, self).post()
            
    @api.multi
    def register_reconcile(self, line_to_reconcile, payment_line, writeoff_acc_id=False, writeoff_journal_id=False):
        """ Reconcile payable/receivable lines from the invoice with payment_line """
        return (line_to_reconcile + payment_line).reconcile(writeoff_acc_id, writeoff_journal_id)
    
    @api.multi
    def button_cancel(self):
        self.line_ids.remove_move_reconcile()
        return super(AccountMove, self).button_cancel()
    
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _description = "Account Move Line"
    
    move_line_id = fields.Many2one('account.move.line', string='Transaction')
    is_debit_partner = fields.Boolean('Is Debit Partner')
    is_credit_partner = fields.Boolean('Is Credit Partner')
    is_debit_invoice = fields.Boolean('Is Debit Transaction')
    is_credit_invoice = fields.Boolean('Is Credit Transaction')
    is_debit_product = fields.Boolean('Is Debit Product')
    is_credit_product = fields.Boolean('Is Credit Product')
    is_reconcile = fields.Boolean('Is Reconcile')
    
    @api.onchange('account_id')
    def onchange_account_id(self):
        if not self.move_id.is_general:
            return
        debits = []
        credits = []
        debits_type = []
        credits_type = []
        for debit_acc in self.move_id.general_debit_account_ids:
            debits.append(debit_acc.id)
            debits_type.append(debit_acc.user_type_id.name)
        for credit_acc in self.move_id.general_credit_account_ids:
            credits.append(credit_acc.id)
            credits_type.append(credit_acc.user_type_id.name)
        #IF RECONCILE
        #print "====self.account_id.reconcile====",self.account_id.reconcile,self.journal_id.is_debit_reconcile,self.journal_id.is_credit_reconcile
        self.is_reconcile = self.account_id.reconcile and self.account_id.reconcile == (self.journal_id.is_debit_reconcile or self.journal_id.is_credit_reconcile) and True or False
        #IF STUDENT & CUSTOMER & SUPPLIER
        if self.account_id.id in debits and (self.move_id.journal_id.debit_student or self.move_id.journal_id.debit_customer or self.move_id.journal_id.debit_supplier):
            self.is_debit_partner = True
        else:
            self.is_debit_partner = False
        if self.account_id.id in credits and (self.move_id.journal_id.credit_student or self.move_id.journal_id.credit_customer or self.move_id.journal_id.credit_supplier):
            self.is_credit_partner = True
        else:
            self.is_credit_partner = False
        #IF PRODUCT
        if self.account_id.id in debits and self.move_id.journal_id.debit_product:
            self.is_debit_product = True
        else:
            self.is_debit_product = False
        if self.account_id.id in credits and self.move_id.journal_id.credit_product:
            self.is_credit_product = True
        else:
            self.is_credit_product = False
        #IF MOVE LINE
        if self.account_id.id in debits and self.move_id.journal_id.debit_invoice:
            self.is_debit_invoice = True
        else:
            self.is_debit_invoice = False
        if self.account_id.id in credits and self.move_id.journal_id.credit_invoice:
            self.is_credit_invoice = True
        else:
            self.is_credit_invoice = False

    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        if not self.invoice_id:
            return
        move_line_id = False
        if self.invoice_id.move_id:
            for line in self.invoice_id.move_id.line_ids:
                if line.account_id == self.invoice_id.account_id:
                    move_line_id = line.id
        self.move_line_id = move_line_id
        
    @api.onchange('debit', 'account_id', 'move_id.is_general', 'move_id.general_debit_account_ids')
    def onchange_debit_id(self):
        if not self.move_id.is_general:
            return
        debits = []
        for debit_acc in self.move_id.general_debit_account_ids:
            debits.append(debit_acc.id)
        if self.account_id.id not in debits:
            self.credit = self.debit
            self.debit = 0.0
                
    @api.onchange('credit', 'account_id', 'move_id.is_general', 'move_id.general_credit_account_ids')
    def onchange_credit_id(self):
        if not self.move_id.is_general:
            return
        credits = []
        for credit_acc in self.move_id.general_credit_account_ids:
            credits.append(credit_acc.id)
        if self.account_id.id not in credits:
            self.debit = self.credit 
            self.credit = 0.0
            
         