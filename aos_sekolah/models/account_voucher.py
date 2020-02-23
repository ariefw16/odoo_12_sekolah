# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from odoo import fields, models, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from . import amount_to_text

class AccountVoucher(models.Model):
    _name    = "account.voucher"
    _description = 'Accounting Voucher'
    _inherit = ['account.voucher', 'mail.thread']

    @api.one
    def _amount2text_idr(self):
        for voucher in self:
            if voucher.currency_id:
                self.check_amount_in_words_id = amount_to_text.amount_to_text(math.floor(voucher.amount), 'id', voucher.currency_id.name)
            else:
                self.check_amount_in_words_id = amount_to_text.amount_to_text(math.floor(voucher.amount), lang='en', currency='')
        return self.check_amount_in_words_id
    
    @api.model
    def _default_journal(self):
        voucher_type = self._context.get('voucher_type', 'cash')
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', '=', voucher_type),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)
    
#     @api.multi
#     @api.depends('tax_correction', 'amount_payment', 'line_ids.price_subtotal')
#     def _compute_total(self):
#         for voucher in self:
#             total = 0
#             tax_amount = 0
#             for line in voucher.line_ids:
#                 tax_info = line.tax_ids.compute_all(line.price_unit, voucher.currency_id, line.quantity, line.product_id, voucher.partner_id)
#                 total += tax_info.get('total_included', 0.0)
#                 tax_amount += sum([t.get('amount',0.0) for t in tax_info.get('taxes', False)]) 
#             voucher.amount = total + voucher.tax_correction
#             voucher.amount_change = voucher.amount - voucher.amount_payment
#             voucher.tax_amount = tax_amount
            
    number = fields.Char(readonly=False, copy=False)
    #account_id = fields.Many2one('account.account', 'Account', required=True, readonly=True, states={'draft': [('readonly', False)]},  domain="[('deprecated', '=', False)]")
    #voucher_type = fields.Selection([('sale', 'Receipt'), ('purchase', 'Payment')], string='Type', required=True, readonly=True, states={'draft': [('readonly', False)]}, oldname="type", default='sale')
    # domain="[('type','!=','situation'),('type','in',('cash','bank'))]"
    journal_id = fields.Many2one('account.journal', 'Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_journal,
        domain="[('type','!=','situation'),('type','=', (payment_type == 'cash' and 'cash' or 'bank'))]"
        )
    user_id = fields.Many2one('res.users', 'Petugas', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user)
    
    account_id = fields.Many2one('account.account', 'Account',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        domain="[('deprecated', '=', False), ('internal_type','=', (pay_now == 'pay_now' and 'liquidity' or voucher_type == 'purchase' and 'payable' or 'receivable'))]")
    voucher_account_ids = fields.Many2many('account.account', 'account_move_voucher_ids_rel', 'voucher_id', 'account_id', string='Default Account',
        domain=[('deprecated', '=', False)], help="It acts as a default account for debit amount")
    
#     voucher_type = fields.Selection(selection_add=[('advance_sale', 'Advance Sale'),
#         ('advance_purchase', 'Advance Purchase'),])
    payment_type = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ], 'Payment', index=True, readonly=True, states={'draft': [('readonly', False)]}, default='cash')
    #transaction_type = fields.Selection([('expedition', 'Expedition'), ('regular', 'Regular'),('disposal','Asset Disposal')], string='Transaction Type', readonly=True, states={'draft': [('readonly', False)]})
#     amount_payment = fields.Float('Payment')
#     amount_change = fields.Monetary(string='Change', store=True, readonly=True, compute='_compute_total')
    check_amount_in_words_id = fields.Char(string='Amount in Words', readonly=True, compute='_amount2text_idr') 
    
    @api.onchange('partner_id', 'pay_now', 'payment_type')
    def onchange_partner_id(self):
        #print "==onchange_partner_id==",self.pay_now,self.voucher_type
        if self.pay_now == 'pay_now':
            if self.journal_id.type in ('sale','purchase'):
                liq_journal = self.env['account.journal'].search([('type','not in',['sale','purchase'])], limit=1)
                self.account_id = liq_journal.default_debit_account_id \
                    if self.voucher_type == 'sale' else liq_journal.default_credit_account_id
            else:
                liq_journal = self.env['account.journal'].search([('type','=',self.payment_type)], limit=1)
                self.journal_id = liq_journal.id
                self.account_id = self.journal_id.default_debit_account_id \
                    if self.voucher_type == 'sale' else self.journal_id.default_credit_account_id
        else:
            if self.partner_id:
                self.account_id = self.partner_id.property_account_receivable_id \
                    if self.voucher_type == 'sale' else self.partner_id.property_account_payable_id
            elif self.journal_id.type not in ('sale','purchase'):
                self.account_id = False
            else:
                self.account_id = self.journal_id.default_debit_account_id \
                    if self.voucher_type == 'sale' else self.journal_id.default_credit_account_id
        voucher_accs = []
        for vacc in self.partner_id.fee_line:
            if vacc.product_id.property_account_advance_id:
                voucher_accs.append(vacc.product_id.property_account_advance_id.id)
        self.voucher_account_ids = voucher_accs
                
#     @api.multi
#     def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
#         '''
#         Create one account move line, on the given account move, per voucher line where amount is not 0.0.
#         It returns Tuple with tot_line what is total of difference between debit and credit and
#         a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).
# 
#         :param voucher_id: Voucher id what we are working with
#         :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
#         :param move_id: Account move wher those lines will be joined.
#         :param company_currency: id of currency of the company to which the voucher belong
#         :param current_currency: id of currency of the voucher
#         :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
#         :rtype: tuple(float, list of int)
#         '''
#         for voucher in self:
#             for line in voucher.line_ids:
#                 #print "voucher",voucher.voucher_type
#                 #create one move line per voucher line where amount is not 0.0
#                 if not line.price_subtotal:
#                     continue
#                 # convert the amount set on the voucher line into the currency of the voucher's company
#                 # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
#                 amount = self._convert_amount(line.price_unit*line.quantity)
#                 if voucher.voucher_type == 'sale':
#                     if amount < 0.0: 
#                         debit = abs(amount)
#                         credit = 0.0
#                     else:                        
#                         debit = 0.0
#                         credit = abs(amount)
#                 elif voucher.voucher_type == 'purchase':
#                     if amount < 0.0: 
#                         debit = 0.0
#                         credit = abs(amount)
#                     else:                
#                         debit = abs(amount)
#                         credit = 0.0          
#                 move_line = {
#                     'journal_id': self.journal_id.id,
#                     'name': line.name or '/',
#                     'account_id': line.account_id.id,
#                     'move_id': move_id,
#                     'partner_id': self.partner_id.id,
#                     'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
#                     'quantity': 1,
#                     'credit': credit,#abs(amount) if (amount < 0.0 or voucher.voucher_type == 'sale') else 0.0,#abs(amount) if self.voucher_type == 'sale' else 0.0,
#                     'debit': debit,#abs(amount) if (amount > 0.0 and voucher.voucher_type == 'purchase') else 0.0,#abs(amount) if self.voucher_type == 'purchase' else 0.0,
#                     'date': self.date,
#                     'tax_ids': [(4,t.id) for t in line.tax_ids],
#                     'amount_currency': line.price_subtotal if current_currency != company_currency else 0.0,
#                 }
#                 self.env['account.move.line'].create(move_line)
#         return line_total

#     @api.multi
#     def first_move_line_get(self, move_id, company_currency, current_currency):
#         debit = credit = 0.0
#         if self.voucher_type == 'purchase':
#             credit = self._convert_amount(self.amount_payment)
#         elif self.voucher_type == 'sale':
#             debit = self._convert_amount(self.amount_payment)
#         if debit < 0.0: debit = 0.0
#         if credit < 0.0: credit = 0.0
#         sign = debit - credit < 0 and -1 or 1
#         #set the first line of the voucher
#         move_line = {
#                 'name': self.name or '/',
#                 'debit': debit,
#                 'credit': credit,
#                 'account_id': self.account_id.id,
#                 'move_id': move_id,
#                 'journal_id': self.journal_id.id,
#                 'partner_id': self.partner_id.id,
#                 'currency_id': company_currency != current_currency and current_currency or False,
#                 'amount_currency': (sign * abs(self.amount)  # amount < 0 for refunds
#                     if company_currency != current_currency else 0.0),
#                 'date': self.account_date,
#                 'date_maturity': self.date_due,
#                 'payment_id': self._context.get('payment_id'),
#             }
#         return move_line
#     
#     @api.multi
#     def last_move_line_get(self, move_id, company_currency, current_currency):
#         debit = credit = 0.0
#         if self.voucher_type == 'purchase':
#             debit = self._convert_amount(abs(self.amount_change))
#         elif self.voucher_type == 'sale':
#             credit = self._convert_amount(abs(self.amount_change))
#         if credit < 0.0: debit = 0.0
#         if debit < 0.0: credit = 0.0
#         sign = debit - credit < 0 and -1 or 1
#         #set the first line of the voucher
#         move_line = {
#                 'name': self.name or '/',
#                 'debit': debit,
#                 'credit': credit,
#                 'account_id': self.account_id.id,
#                 'move_id': move_id,
#                 'journal_id': self.journal_id.id,
#                 'partner_id': self.partner_id.id,
#                 'currency_id': company_currency != current_currency and current_currency or False,
#                 'amount_currency': (sign * abs(self.amount_change)  # amount < 0 for refunds
#                     if company_currency != current_currency else 0.0),
#                 'date': self.account_date,
#                 'date_maturity': self.date_due,
#                 'payment_id': self._context.get('payment_id'),
#             }
#         return move_line
#     
#     @api.multi
#     def action_move_line_create(self):
#         '''
#         Confirm the vouchers given in ids and create the journal entries for each of them
#         '''
#         for voucher in self:
#             local_context = dict(self._context, force_company=voucher.journal_id.company_id.id)
#             if voucher.move_id:
#                 continue
#             company_currency = voucher.journal_id.company_id.currency_id.id
#             current_currency = voucher.currency_id.id or company_currency
#             # we select the context to use accordingly if it's a multicurrency case or not
#             # But for the operations made by _convert_amount, we always need to give the date in the context
#             ctx = local_context.copy()
#             ctx['date'] = voucher.account_date
#             ctx['check_move_validity'] = False
#             # Create a payment to allow the reconciliation when pay_now = 'pay_now'.
#             if self.pay_now == 'pay_now' and self.amount > 0:
#                 ctx['payment_id'] = self.env['account.payment'].create(self.voucher_pay_now_payment_create()).id
#             # Create the account move record.
#             move = self.env['account.move'].create(voucher.account_move_get())
#             # Get the name of the account_move just created
#             # Create the first line of the voucher
#             move_line = self.env['account.move.line'].with_context(ctx).create(voucher.with_context(ctx).first_move_line_get(move.id, company_currency, current_currency))
#             line_total = move_line.debit - move_line.credit
#             if voucher.voucher_type == 'sale':
#                 line_total = line_total - voucher._convert_amount(voucher.tax_amount)
#             elif voucher.voucher_type == 'purchase':
#                 line_total = line_total + voucher._convert_amount(voucher.tax_amount)
#             # GET CHARGE
#             if voucher.voucher_type == 'sale':
#                 line_total = line_total - voucher._convert_amount(voucher.amount)
#             elif voucher.voucher_type == 'purchase':
#                 line_total = line_total + voucher._convert_amount(voucher.amount)
#             # Create one move line per voucher line where amount is not 0.0
#             line_total = voucher.with_context(ctx).voucher_move_line_create(line_total, move.id, company_currency, current_currency)
#             # IF CHARGE IS POSITIVE
#             if line_total > 0:
#                 move_line = self.env['account.move.line'].with_context(ctx).create(voucher.with_context(ctx).last_move_line_get(move.id, company_currency, current_currency))
#             if line_total < 0:
#                 raise UserError(_("Amount Payment should be greater than Amount Total!"))
#             # Add tax correction to move line if any tax correction specified
#             if voucher.tax_correction != 0.0:
#                 tax_move_line = self.env['account.move.line'].search([('move_id', '=', move.id), ('tax_line_id', '!=', False)], limit=1)
#                 if len(tax_move_line):
#                     tax_move_line.write({'debit': tax_move_line.debit + voucher.tax_correction if tax_move_line.debit > 0 else 0,
#                         'credit': tax_move_line.credit + voucher.tax_correction if tax_move_line.credit > 0 else 0})
# 
#             # We post the voucher.
#             voucher.write({
#                 'move_id': move.id,
#                 'state': 'posted',
#                 'number': move.name
#             })
#             move.post()
#         return True
    
#     @api.onchange('partner_id', 'pay_now')
#     def onchange_partner_id(self):
#         if self.pay_now == 'pay_now':
#             liq_journal = self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))], limit=1)
#             self.account_id = liq_journal.default_debit_account_id \
#                 if self.voucher_type == 'sale' else liq_journal.default_credit_account_id
#         else:
#             if self.partner_id:
#                 self.account_id = self.partner_id.property_account_receivable_id \
#                     if self.voucher_type == 'sale' else self.partner_id.property_account_payable_id
#             else:
#                 self.account_id = self.journal_id.default_debit_account_id \
#                     if self.voucher_type == 'sale' else self.journal_id.default_credit_account_id

class AccountVoucherLine(models.Model):
    _inherit = 'account.voucher.line'
    
    @api.model
    def _default_account(self):
        account_ids = self._context.get('voucher_account_ids')
        accs = []
        if account_ids:
            accs = account_ids[0][2][0]
        return accs
    
    account_id = fields.Many2one('account.account', string='Account',
        required=True,
        default=_default_account,
        help="The income or expense account related to the selected product.")