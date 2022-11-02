# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
from openerp.osv import fields, osv

class presupuesto_reports(osv.osv_memory):
    _name = "presupuesto.reports"
    _description = "Imprimir Presupuesto"

    _columns = {
        'chart_rubros_id': fields.many2one('presupuesto.rubros', 'Plan de Rubros', required=True, domain = [('parent_id','=', False)]),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Año fiscal', select=True, required=True),
        'company_id': fields.related('chart_rubros_id', 'company_id', type='many2one', relation='res.company', string='Company', readonly=True),
        'move_id': fields.many2one('presupuesto.move', 'Movimiento', select=True, required=True),
        'period_from': fields.related('move_id', 'period_id', string='Period', type='many2one', relation='account.period', select=True, store=True),
        'period_to': fields.related('move_id', 'period_id', string='Period', type='many2one', relation='account.period', select=True, store=True),
    }

    def _get_rubros(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        rubros = self.pool.get('presupuesto.rubros').search(cr, uid, [('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return rubros and rubros[0] or False

    def _get_fiscalyear(self, cr, uid, context=None):
        if context is None:
            context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = context.get('active_ids', [])
        if ids and context.get('active_model') == 'presupuesto.rubros':
            company_id = self.pool.get('presupuesto.rubros').browse(cr, uid, ids[0], context=context).company_id.id
        else:  # use current company id
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = self.pool.get('account.fiscalyear').search(cr, uid, domain, limit=1)
        return fiscalyears and fiscalyears[0] or False

    _defaults = {
        'chart_rubros_id': _get_rubros,
        'fiscalyear_id': _get_fiscalyear,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.common.report',context=c),
    }

    def create_presupuesto_reports(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'presupuesto.rubros'
        datas['form'] = self.read(cr, uid, ids, context=context)[0]
        for field in datas['form'].keys():
            if isinstance(datas['form'][field], tuple):
                datas['form'][field] = datas['form'][field][0]
        datas['form']['company_id'] = self.pool.get('presupuesto.rubros').browse(cr, uid, [datas['form']['chart_rubros_id']], context=context)[0].company_id.id
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'presupuesto_reports',
            'datas': datas,
        }

presupuesto_reports()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
