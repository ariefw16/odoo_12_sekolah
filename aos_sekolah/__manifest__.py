# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2017 Alphasoft
#    (<http://www.alphasoft.co.id>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Sistem Informasi Sekolah',
    'version': '12.0.0.1.0',
    'author': "Alphasoft",
    'sequence': 1,
    'website': 'http://www.alphasoft.co.id',
    'license': 'AGPL-3',
    'category': 'Accounting',
    'summary': 'Sekolah of a module by Alphasoft.',
    'depends': ['base', 
                'account', 
                # 'account_asset', 
                #'point_of_sale', 
                'stock_account', 
                'purchase', 
                'account_voucher',
                'hr',
                # 'aos_report_webkit'
                ],
    'description': """
Module based on Alphasoft
===================================================== 
""",
    'demo': [],
    'test': [],
    'data': [
        'security/school_security.xml',
        'security/ir.model.access.csv',
        # 'data/no_header_footer_A5.xml',
        # 'data/no_header_footer_A4.xml',
        'wizard/grade_next_upgrade_view.xml',
        'views/account_menuitem.xml',
        'views/header_menu_view.xml',
        'wizard/advance_voucher_view.xml',
        'views/account_voucher_view.xml',
        'views/school_period_view.xml',
        'views/school_grade_view.xml',
        'views/fee_type_view.xml',
        'views/student_admission_view.xml',
        'views/student_view.xml',
        'views/student_fee_view.xml',
        'views/student_res_config_view.xml',
        'views/res_partner_view.xml',
        'views/product_view.xml',
        # 'views/res_config_view.xml',     --BELUM NEMU--
        # 'report/report_account_view.xml',
        # 'report/student_invoice_report_view.xml',
        'data/student_sequence.xml',
        'data/fee_register_data.xml',
        # 'report/student_report_view.xml',
     ],
    'css': [],
    'js': [],
    'installable': True,
    'auto_install': False,
}
