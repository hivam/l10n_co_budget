# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Budget',
    'version': '1.0',
    'category': 'budget',
    'summary': 'l10n_co_budget',
    'description': """
    """,
    'website': '',
    'depends': ['account', 'base', 'account_voucher', 'hr_contract', 'l10n_co_fiscal_year', 'l10n_co_invoice_amount_to_text'],
    'data': [
        'security/budget_security.xml',
        'security/ir.model.access.csv',
        'views/presupuesto_sequence.xml',
        'views/budget.xml',
        'views/account_voucher_view.xml',
        'views/account_invoice_view.xml',
        'views/hr_contract.xml',
        'views/cargue_view.xml',
        'views/account_payment_view.xml',        
        'wizard/presupuesto_ejecucion_ingresos_view.xml',
        'wizard/presupuesto_ejecucion_ingresos_contables_view.xml',
        'wizard/presupuesto_ejecucion_gastos_view.xml',
        'wizard/presupuesto_ejecucion_gastos_contables_view.xml',
        'wizard/rp_con_saldo_pendiente_view.xml',

    ],
    'update_xml' : [
        'report/gastos.xml',
        'report/ingresos.xml', 
        'report/documentos.xml',
        'report/rp_con_saldo.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
