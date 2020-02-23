# -*- coding: utf-8 -*-
import time
from datetime import date, datetime
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.modules import get_module_resource
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, image_colorize,\
    image_resize_image_big
from odoo.exceptions import except_orm, Warning as UserError
import odoo.addons.decimal_precision as dp

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    asset_ok = fields.Boolean(
        'Is Asset', default=False,
        help="Specify if the product can be asset.") 
    method_valuation = fields.Selection([
        ('manual_periodic', 'Periodic (manual)'),
        ('real_time', 'Perpetual (automated)')], string='Method Valuation',
        copy=True, default='real_time',
        help="If perpetual valuation is enabled for a product, the system will automatically create journal entries corresponding to stock moves, with product price as specified by the 'Costing Method'" \
             "The inventory variation account set on the product category will represent the current inventory value, and the stock input and stock output account will hold the counterpart moves for incoming and outgoing products.")
    property_return_income_account_id = fields.Many2one(
        'account.account', 'Retur Income Account',
        company_dependent=True, domain=[('deprecated', '=', False)])
    property_asset_account_id = fields.Many2one(
        'account.account', 'Asset Account',
        company_dependent=True, domain=[('deprecated', '=', False)])
#     property_product_valuation_account_id = fields.Many2one(
#         'account.account', 'Inventory Account',
#         company_dependent=True, domain=[('deprecated', '=', False)]) 
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable",
        domain="[('name', 'ilike', 'PIUTANG'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current product",
        required=False)
    property_account_advance_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Advance",
        domain="[('internal_type','=','receivable'),('deprecated','=',False),'|',('name', 'ilike', 'ADVANCE'),('name', 'ilike', 'UANG MUKA')]",
        help="This account will be used instead of the default one as the advance account for the current product",
        required=False)
    property_account_advance_buy_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Buy",
        domain="[('internal_type','=','receivable'),('deprecated','=',False),'|',('name', 'ilike', 'UANG MUKA'),('name', 'ilike', 'ADVANCE')]",
        help="This account will be used instead of the default one as the advance account for the current product",
        required=False)
    
    @api.multi
    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super(ProductTemplate, self)._get_product_accounts()
        res = self._get_asset_accounts()
        accounts.update({
            'asset': self.property_asset_account_id or self.categ_id.property_asset_account_categ_id,
            'return_income': self.property_return_income_account_id or self.categ_id.property_return_income_account_categ_id,
        })
        return accounts
    
class ProductProduct(models.Model):
    _inherit = "product.product"
    
    is_fee = fields.Boolean('Is Fee', default=lambda self: self._context.get('is_fee', False))
    
    @api.multi
    @api.depends('fee_line')
    def name_get(self):
        context = self._context or {}
        result = []
        fee_reg_line = self.env['fee.register.line']
        for product in self:
            #print "====product====",product
            if context.get('is_school') and context.get('partner_id'):
                fee_reg_ids = fee_reg_line.search([('product_id','=',product.id),('partner_id','=',context.get('partner_id'))])
                if fee_reg_ids:
                    if product.default_code:
                        name = '['+product.default_code+'] ' + product.name
                    else:
                        name = product.name
                    result.append((product.id, name))
            else:
                result.append((product.id, product.name))
        return result


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_return_income_account_categ_id = fields.Many2one(
        'account.account', 'Retur Income Account',
        company_dependent=True, domain=[('deprecated', '=', False)])
    property_asset_account_categ_id = fields.Many2one(
        'account.account', 'Asset Account',
        company_dependent=True, domain=[('deprecated', '=', False)])

class FeeType(models.Model):
    '''Fees structure'''
    _name = 'fee.type'
    _description = 'Student Fees Structure'

    name = fields.Char('Nama', required=True)
    code = fields.Char('Kode', required=False)
    bill_type = fields.Selection([('reg_bill', 'Registration Fee'),
                             ('package', 'Package'),
                             ('once', 'Once Payment')], 'Type', required=False)
    state = fields.Selection([('draft', 'Draft'),
                             ('confirm', 'Verified')], 'Status', default='draft')
    line_ids = fields.Many2many('fee.line','student_fees_structure_payslip_rel', 'fee_id', 'line_id', 'Fees Items')

    _sql_constraints = [('code_uniq', 'unique(code)', 'The code of the Fees Structure must be unique !')]
    
class FeeLine(models.Model):
    '''Student Fees Structure Line'''
    _name = 'fee.line'
    _description = 'Student Fees Structure Line'
    _order = 'sequence'

    sequence = fields.Integer('Sequence')
    product_id = fields.Many2one('product.product', 'Product', required=True, delegate=True, ondelete='cascade')
   #name = fields.Char('Description', required=True)
    type = fields.Selection([('monthly', 'Month(s)'),
                             ('yearly', 'Year(s)'),
                             ('once', 'Once Payment'),
                             ('advance', 'Advance')], 'Duration', required=True)
    quantity = fields.Float('Number Calls',default=1.0, digits=dp.get_precision('Product Unit of Measure'))
    amount = fields.Float('Fix Amount', digits=(16, 2))
    state = fields.Selection([('draft', 'Draft'),
                             ('confirm', 'Verified')], 'Status', default='draft')
    
#     @api.onchange('product_id')
#     def _onchange_product_id(self):
#         if not self.product_id:
#             return
#         self.name = self.product_id.name
    
    @api.onchange('type')
    def _onchange_type(self):
        if not self.type:
            return
        self.quantity = 1
        if self.type in ('monthly','yearly'):
            self.quantity = -1


    
    