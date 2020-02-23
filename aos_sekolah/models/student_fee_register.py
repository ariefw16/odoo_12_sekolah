# -*- coding: utf-8 -*-
import time
from datetime import date, datetime
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.modules import get_module_resource
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATE_FORMAT, image_colorize,\
    image_resize_image_big
from odoo.exceptions import except_orm, Warning as UserError
import logging
from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)
import odoo.addons.decimal_precision as dp
# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#     
#     fee_register_line = fields.One2many('fee.register.line', 'product_id', 'Fee Register Items')

class FeeRegisterLine(models.Model):
    '''Student Fees Structure Line'''
    _name = 'fee.register.line'
    _description = 'Student Fees Register'
    _order = 'sequence'
    
    @api.one
    @api.depends('amount', 'discount', 'invoice_line_tax_ids')
    def _compute_price(self):
        currency = self.partner_id and self.partner_id.currency_id or None
        #price = self.amount
        price = self.amount * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, 1, product=self.product_id, partner=self.partner_id)
        self.amount_subtotal = taxes['total_excluded'] if taxes else price
    
    @api.one    
    @api.depends('invoice_lines', 'invoice_lines.state', 'invoice_lines.invoice_id.state')
    def _compute_state(self):
        for line in self:
            inv_state = 'to_invoice'
            if self.stop or line.qty_to_invoice == 0 or line.partner_id.state in ('alumni','terminate'):
                inv_state = 'done'
            elif self.partner_id.state == 'draft':
                inv_state = 'draft'
            elif self.partner_id.state == 'cancel':
                inv_state = 'cancel'
            elif not line.invoice_lines and self.partner_id.state == 'confirm':
                inv_state = 'confirm'
            else:
                if line.type in ('monthly','yearly') and line.qty_to_invoice > 0:
                    inv_state = 'to_billing'
                else:
                    for inv in line.invoice_lines:
                        inv_state = inv.state                            
            line.state = inv_state
            
        
    @api.depends('qty_invoiced', 'quantity', 'type')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            if line.partner_id.is_student:
                if line.type in ('monthly','yearly') and (line.quantity > line.qty_invoiced or line.quantity == -1):
                    line.qty_to_invoice = 1
                elif line.type == 'once':
                    line.qty_to_invoice = line.quantity - line.qty_invoiced
                else:
                    line.qty_to_invoice = 0
            else:
                line.qty_to_invoice = 0
    
    @api.depends('invoice_lines.invoice_id.state', 'invoice_lines.quantity')
    def _get_invoice_qty(self):
        """
        Compute the quantity invoiced. If case of a refund, the quantity invoiced is decreased. Note
        that this is the case only if the refund is generated from the SO and that is intentional: if
        a refund made would automatically decrease the invoiced quantity, then there is a risk of reinvoicing
        it automatically, which may not be wanted at all. That's why the refund has to be created from the SO
        """
        for line in self:
            qty_invoiced = 0.0
            for inv_line in line.invoice_lines:
                if inv_line.invoice_id.state != 'cancel':
                    if inv_line.invoice_id.type == 'out_invoice':
                        qty_invoiced += inv_line.uom_id._compute_quantity(inv_line.quantity, line.product_id.uom_id)
                    elif inv_line.invoice_id.type == 'out_refund':
                        qty_invoiced -= inv_line.uom_id._compute_quantity(inv_line.quantity, line.product_id.uom_id)
            line.qty_invoiced = qty_invoiced
            
    sequence = fields.Integer('Sequence')
    name = fields.Char('Description', required=False)
    fee_line_id = fields.Many2one('fee.line', 'Name')
    partner_id = fields.Many2one('res.partner', 'Student', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product Related',
        ondelete='restrict', index=True)
    date_start = fields.Date('Date Invoice')
    date_next = fields.Date('Date Next Invoice')
    type = fields.Selection([('monthly', 'Month(s)'), ('yearly', 'Year(s)'),
                             ('once', 'Once Payment'),
                             ('advance', 'Advance')], 'Durasi', required=True)
    quantity = fields.Float('Number Calls',default=1.0, digits=dp.get_precision('Product Unit of Measure'))
    qty_to_invoice = fields.Integer(
        compute='_get_to_invoice_qty', string='To Invoice', store=True, readonly=True,
        digits=dp.get_precision('Product Unit of Measure'))
    qty_invoiced = fields.Float(
        compute='_get_invoice_qty', string='Invoiced', store=True, readonly=True,
        digits=dp.get_precision('Product Unit of Measure'))
    amount = fields.Float(string='Amount', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float(string='Discount', required=True, digits=dp.get_precision('Discount'))
    invoice_line_tax_ids = fields.Many2many('account.tax',
        'fee_register_line_tax', 'fee_line_id', 'tax_id',
        string='Taxes', domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)])
    amount_subtotal = fields.Monetary(string='Total',
        store=True, readonly=True, compute='_compute_price')
    invoice_lines = fields.Many2many('account.invoice.line', 'fee_register_line_invoice_rel', 'fee_line_id', 'invoice_line_id', string='Invoice Lines', copy=False)
    
    currency_id = fields.Many2one('res.currency', related='partner_id.currency_id', store=True)
    stop = fields.Boolean('Stop')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirm'),
                              ('to_invoice', 'To Invoice'),
                              ('to_billing', 'Recurrent'),
                              ('open', 'Invoiced'),
                              ('done', 'Done'),
                              ('cancel', 'Cancelled'),
                              ('paid', 'Paid')], 'Status', compute='_compute_state')
    @api.multi
    def unlink(self):
        for line in self:
            if line.state not in ('draft','cancel'):
                raise exceptions.Warning(_('You can only delete a record that in draft or cancel state!'))
        return super(FeeRegisterLine, self).unlink()

    @api.onchange('fee_line_id')
    def _onchange_fee_line_id(self):
        domain = {}
        if not self.fee_line_id:
            return
        self.product_id = self.fee_line_id.product_id
        if self.partner_id and self.partner_id.nis:
            self.name = self.partner_id.nis+': '+self.fee_line_id.product_id.name
        self.partner_id = self.partner_id.id
        self.sequence = self.fee_line_id.sequence
        self.type = self.fee_line_id.type
        self.amount = self.fee_line_id.amount
        self.quantity = self.fee_line_id.quantity or 1
        self.state = 'draft'
    
    @api.multi
    def invoice_line_create(self, invoice_id, qty):
        """
        Create an invoice line. The quantity to invoice can be positive (invoice) or negative
        (refund).
 
        :param invoice_id: integer
        :param qty: float quantity to invoice
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if not float_is_zero(qty, precision_digits=precision):
                vals = line._prepare_invoice_line(qty=qty)
                vals.update({'invoice_id': invoice_id, 'fee_line_ids': [(6, 0, [line.id])]})
                self.env['account.invoice.line'].create(vals)

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        invoice_vals = {
            'name': '',
            'origin': self.name,
            'type': 'out_invoice',
            #AMBIL AKUN DARI FEE
            'account_id': self.product_id and self.product_id.property_account_receivable_id.id or self.partner_id.property_account_receivable_id.id,
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'journal_id': journal_id,
            'currency_id': self.partner_id.currency_id.id,
            'comment': self.partner_id.remark,
            'payment_term_id': False,
            'fiscal_position_id': self.partner_id.property_account_position_id.id,
            'company_id': self.partner_id.company_id.id,
            'level_id': self.partner_id.level_id.id,
            'year_id': self.partner_id.year_id.id,
            'grade_id': self.partner_id.grade_id.id,
            'grade_line_id': self.partner_id.grade_line_id.id,
        }
        #print "===vals===",invoice_vals
        return invoice_vals
    
    @api.multi
    def _action_invoice_create(self, automatic=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        fee_line_obj = self.env['fee.register.line']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        current_date = fields.Date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years', 'once': 'days'}
        if not automatic:
            #print "IF MANUAL"
            for line in self:
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                inv_data = line._prepare_invoice()
                inv_data.update({'date_next': current_date})
                invoice = inv_obj.create(inv_data)
                if line.qty_to_invoice > 0:
                    line.invoice_line_create(invoice.id, line.qty_to_invoice)
        else:
            #print "ELSE CRON"
            domain = [('id', 'in', self.ids)] if self.ids else [('date_next', '<=', current_date), ('qty_to_invoice', '>', 0),('stop','=',False)]
            subs = fee_line_obj.search(domain)
            for line in subs:
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                inv_data = line._prepare_invoice()
                inv_data.update({'date_invoice': line.date_next})
                invoice = inv_obj.create(inv_data)
                if line.qty_to_invoice > 0:
                    line.invoice_line_create(invoice.id, line.qty_to_invoice)
                next_date = fields.Date.from_string(line.date_next or current_date)
                rule, interval = line.type, line.qty_to_invoice
                new_date = next_date + relativedelta(**{periods[rule]: interval})
                line.write({'date_next': new_date})
        return True
    
    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.
 
        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = {}
        account = self.product_id.property_account_income_id or self.product_id.categ_id.property_account_income_categ_id
        if not account:
            raise UserError(_('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (self.product_id.name, self.product_id.id, self.product_id.categ_id.name))
 
        fpos = self.partner_id.property_account_position_id
        if fpos:
            account = fpos.map_account(account)
 
        res = {
            'name': self.product_id.name,
            'sequence': self.sequence,
            'origin': self.name,
            'account_id': account.id,
            'price_unit': self.amount,
            'quantity': qty,
            'discount': self.discount,
            'uom_id': self.product_id.uom_id.id,
            'product_id': self.product_id.id or False,
            'invoice_line_tax_ids': [(6, 0, self.invoice_line_tax_ids.ids)],
            'account_analytic_id': False,
            'analytic_tag_ids': False,
        }
        return res
    
    @api.multi
    def action_invoice(self):
        """ INI UNTUK MANUAL GENERATE INVOICE"""
        return self._action_invoice_create()
    
    @api.model
    def _cron_recurring_create_invoice_fee(self):
        print (""" INI UNTUK AUTOMATIC GENERATE INVOICE BY CRON""",self)
        return self._action_invoice_create(automatic=True)
    
    @api.multi
    def action_stop_invoice(self):
        """ INI UNTUK STOP GENERATE INVOICE"""
        return self.write({'stop': True})
    
class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
     
    product_id = fields.Many2one('product.product', related='invoice_line_ids.product_id', string='Product')
    year_id = fields.Many2one('school.year', 'School Year')
    level_id = fields.Many2one('school.level', 'Level')
    grade_id = fields.Many2one('school.grade', 'Grade')
    grade_line_id = fields.Many2one('school.grade.line', 'Classroom')
    
    @api.model
    def _anglo_saxon_sale_move_lines(self, i_line):
        """Return the additional move lines for sales invoices and refunds.

        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id
        
        if i_line.product_id.type == 'product' and i_line.product_id.valuation == 'manual_periodic' and i_line.product_id.method_valuation == 'real_time':
            fpos = i_line.invoice_id.fiscal_position_id
            accounts = i_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)
            # debit account dacc will be the output account
            dacc = accounts['stock_output'].id #HPP
            # credit account cacc will be the expense account
            cacc = accounts['expense'].id #PERSEDIAAN
            if dacc and cacc:
                price_unit = i_line._get_anglo_saxon_price_unit()
                return [
                    {
                        'type': 'src',
                        'name': i_line.name[:64],
                        'price_unit': price_unit,
                        'quantity': i_line.quantity,
                        'price': i_line._get_price(company_currency, price_unit),
                        'account_id':dacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': i_line.account_analytic_id.id,
                        'analytic_tag_ids': i_line.analytic_tag_ids.ids and [(6, 0, i_line.analytic_tag_ids.ids)] or False,
                    },

                    {
                        'type': 'src',
                        'name': i_line.name[:64],
                        'price_unit': price_unit,
                        'quantity': i_line.quantity,
                        'price': -1 * i_line._get_price(company_currency, price_unit),
                        'account_id':cacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': i_line.account_analytic_id.id,
                        'analytic_tag_ids': i_line.analytic_tag_ids.ids and [(6, 0, i_line.analytic_tag_ids.ids)] or False,
                    },
                ]
        return []

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    _order = 'invoice_id, sequence, id'
    
    state = fields.Selection([
            ('draft','Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', related='invoice_id.state', store=True)
    fee_line_ids = fields.Many2many(
        'fee.register.line',
        'fee_register_line_invoice_rel',
        'invoice_line_id', 'fee_line_id',
        string='Fee Register Lines', readonly=True, copy=False)

class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"
    _description = "Invoice Tax"
    _order = 'sequence'

    partner_id = fields.Many2one('res.partner', string='Fee', ondelete='cascade', index=True)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
#     @api.multi
#     def _fee_total(self):
#         if not self.ids:
#             self.total_fee = 0.0
#             return True
#         total = 0.0
#         register = self.env['fee.register'].search([('partner_id','in',self.ids)])
#         for reg in register:
#             total += reg.amount_total
#         self.total_fee = total          
    
    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            # ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))), -- NOTE THIS ! Search More
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)
    
    #total_fee = fields.Monetary(compute='_fee_total', string="Total Fee")
    fee_id = fields.Many2one('fee.type', 'Struktur Biaya', required=False)
    fee_line = fields.One2many('fee.register.line', 'partner_id', string='Biaya')
    tax_line_ids = fields.One2many('account.invoice.tax', 'partner_id', string='Tax Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    
    @api.onchange('fee_line')
    def _onchange_fee_line_ids(self):
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
        return
    
    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.fee_line:
            price_unit = line.amount# * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped
    
    def _prepare_tax_line_vals(self, line, tax):
        """ Prepare values to create an account.invoice.tax line

        The line parameter is an account.invoice.line, and the
        tax parameter is the output of account.tax.compute_all().
        """
        vals = {
            'fee_id': self.id,
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': tax['amount'],
            'base': tax['base'],
            'manual': False,
            'sequence': tax['sequence'],
            'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
            'account_id': self.type in ('out_invoice', 'in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
        }
        return vals
    
    def _prepare_register_from_fee_line(self, line):
        register_line = self.env['fee.register.line']
        data = {
            'sequence': line.sequence,
            'fee_line_id': line.id,
            'name': self.fee_id.name+': '+line.name,
            'type': line.type,
            'product_id': line.product_id.id,
            'amount': line.list_price,#line.order_id.currency_id.compute(line.price_unit, self.currency_id, round=False),
            'quantity': line.quantity or 1,
            'state': 'draft',
            #'account_analytic_id': line.account_analytic_id.id,
            #'analytic_tag_ids': line.analytic_tag_ids.ids,
            #'invoice_line_tax_ids': invoice_line_tax_ids.ids
        }
        return data
    
    # Load all unsold Fee lines
    @api.onchange('fee_id')
    def fee_register_change(self):
        new_lines = self.env['fee.register.line']
        for line in self.fee_id.line_ids:
            if line in self.fee_line.mapped('fee_line_id'):
                continue
            data = self._prepare_register_from_fee_line(line)
            new_line = new_lines.new(data)
            new_lines += new_line 
        self.fee_line += new_lines
        return {}
    