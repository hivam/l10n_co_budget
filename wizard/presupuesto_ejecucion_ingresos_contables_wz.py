# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import json
import logging
from openerp.http import request
import time
import base64

try:
    import xlsxwriter
except ImportError:
    _logger.debug('Can not import xlsxwriter`.')

import logging

_logger = logging.getLogger(__name__)


class presupuesto_ejecucion_ing_contables(models.TransientModel):
	_name = "presupuesto.ejecucion.ingresos.contables"
	_description = "Ejecucion de Ingresos Contables"

	chart_rubros_id = fields.Many2one('presupuesto.rubros', 'Plan de Rubros', required=True, domain = [('parent_id','=', False)], ondelete = 'cascade')
	fiscalyear_id =  fields.Many2one('account.fiscalyear', u'Año fiscal', select=True, required=True)
	company_id = fields.Many2one('res.company', 'Company', related = 'chart_rubros_id.company_id')
	period_from = fields.Many2one('account.period', 'Periodo inicial', required=True)
	period_to =  fields.Many2one('account.period', 'Periodo final', required=True)
	period_ant =  fields.Many2one('account.period', 'Periodo anterior')

	data_ids = fields.One2many('presupuesto.ejecucion.ingresos.contables.report', 'active_id', 'Records')
	excel_file_name = fields.Char('Nombre archivo excel')
	excel_file = fields.Binary('Archivo excel generado:', readonly='True')


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

	@api.onchange('period_to')
	def onchange_period(self):

		
		if self.period_to:

			period = self.period_to
			year = period.fiscalyear_id.id
			period_0 = period.id - 1
			period_0 = self.env['account.period'].browse(period_0)
			year_0 = period_0.fiscalyear_id.id
			special_0 = period_0.special
			if year == year_0 and special_0 == False:
				period_0 = period_0.id
			else:
				period_0 = None

			self.period_ant = period_0	


	@api.multi
	def create_presupuesto_ejecucion_ing_contables_excel(self):
		
		datos = self.env['presupuesto.util'].sql({'rubro_tipo' : 'I'}, {
			'active_model' : 'presupuesto.ejecucion.ingresos.contables',
			'active_id' : self.id
		})
		if datos:
			datos = datos[ 0 ]

			self.env.cr.execute('delete from presupuesto_ejecucion_ingresos_contables_report where active_id = %s' % ( self.id ))

			sql = 'insert into presupuesto_ejecucion_ingresos_contables_report(active_id, rubro_codigo, rubro_nombre, rubro_nivel, rubro_codigo_cta_contable, rubro_nombre_cta_contable, rubro_amount, adiciones, reducciones, creditos, contracreditos, apropiacion_definitiva, ejecutado_anterior, ejecutado_mes, total_ejecutado, saldo_por_ejecutar, porcentaje) values'
			values = []
			for dato in datos:
				dato.update({
					'active_id' : self.id
				})
				values.append("(%(active_id)s, '%(rubro_codigo)s', '%(rubro_nombre)s', '%(rubro_nivel)s', '%(rubro_codigo_cta_contable)s', '%(rubro_nombre_cta_contable)s', '%(rubro_amount)s', '%(adiciones)s', '%(reducciones)s', '%(creditos)s', '%(contracreditos)s', '%(apropiacion_definitiva)s', '%(ejecutado_anterior)s', '%(ejecutado_mes)s', '%(total_ejecutado)s', '%(saldo_por_ejecutar)s', '%(porcentaje)s')" % dato  )

			sql = sql + ','.join( values )	

			_logger.info( sql )

			self.env.cr.execute( sql )

		workbook = xlsxwriter.Workbook('/tmp/presupuesto_ejecucion_ingresos_contables.xlsx')
		worksheet = workbook.add_worksheet()
		format_company = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left', })
		format_titulo = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
		format_cabecera = workbook.add_format({'bold': True, 'font_size': 12, 'border': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': 'gray'})
		format_celda_str = workbook.add_format({'font_size': 12, 'border': True})
		format_celda_num = workbook.add_format({'font_size': 12, 'border': True, 'num_format': '#,##0.00'})
		worksheet.set_row(3,35)
		worksheet.set_column('A:A',10)
		worksheet.set_column('B:B',30)
		worksheet.set_column('C:C',4)
		worksheet.set_column('D:D',10)
		worksheet.set_column('E:E',30)
		worksheet.set_column('F:M',18)
		company = self.env.user.partner_id.company_id.name
		rec_ingresos = self.sudo().env['presupuesto.ejecucion.ingresos.contables.report'].search([('active_id', '=', self.id)])
		row = 3
		worksheet.merge_range('A1:D1', company, format_company)
		worksheet.merge_range('A3:P3', u'Ejecución de Ingresos Contables', format_titulo)
		worksheet.write(row, 0, 'Rubro', format_cabecera)
		worksheet.write(row, 1, 'Nombre', format_cabecera)
		worksheet.write(row, 2, 'N', format_cabecera)
		worksheet.write(row, 3, 'Cuenta\ncontable', format_cabecera)
		worksheet.write(row, 4, 'Nombre', format_cabecera)
		worksheet.write(row, 5, u'Apropiación\ninicial', format_cabecera)
		worksheet.write(row, 6, 'Adiciones', format_cabecera)
		worksheet.write(row, 7, 'Reducciones', format_cabecera)
		worksheet.write(row, 8, u'Créditos', format_cabecera)
		worksheet.write(row, 9, u'Contra\ncréditos', format_cabecera)
		worksheet.write(row, 10, u'Apropiación\ndefinitiva', format_cabecera)
		worksheet.write(row, 11, 'Ejecutado\nanterior', format_cabecera)
		worksheet.write(row, 12, 'Ejecutado\nmes', format_cabecera)
		worksheet.write(row, 13, 'Total\nejecutado', format_cabecera)
		worksheet.write(row, 14, 'Saldo por\nejecutar', format_cabecera)
		worksheet.write(row, 15, '%', format_cabecera)
		row = 4
		for ingreso in rec_ingresos:
			worksheet.write(row, 0, ingreso.rubro_codigo, format_celda_str)
			worksheet.write(row, 1, ingreso.rubro_nombre, format_celda_str)
			worksheet.write(row, 2, ingreso.rubro_nivel, format_celda_str)
			worksheet.write(row, 3, ingreso.rubro_codigo_cta_contable, format_celda_str)
			worksheet.write(row, 4, ingreso.rubro_nombre_cta_contable, format_celda_str)
			worksheet.write(row, 5, ingreso.rubro_amount, format_celda_num)
			worksheet.write(row, 6, ingreso.adiciones, format_celda_num)
			worksheet.write(row, 7, ingreso.reducciones, format_celda_num)
			worksheet.write(row, 8, ingreso.creditos, format_celda_num)
			worksheet.write(row, 9, ingreso.contracreditos, format_celda_num)
			worksheet.write(row, 10, ingreso.apropiacion_definitiva, format_celda_num)
			worksheet.write(row, 11, ingreso.ejecutado_anterior, format_celda_num)
			worksheet.write(row, 12, ingreso.ejecutado_mes, format_celda_num)
			worksheet.write(row, 13, ingreso.total_ejecutado, format_celda_num)
			worksheet.write(row, 14, ingreso.saldo_por_ejecutar, format_celda_num)
			worksheet.write(row, 15, ingreso.porcentaje, format_celda_num)
			row += 1
			col = 0
		workbook.close()
		archivo_excel = open('/tmp/presupuesto_ejecucion_ingresos_contables.xlsx','rb')
		salida = archivo_excel.read()
		archivo_excel.close()

		self.excel_file_name = 'presupuesto_ejecucion_ingresos_contables.xlsx'
		self.excel_file = base64.b64encode(salida)

		return {'type' : 'ir.actions.act_window', 'res_model' : self._name, 'res_id' : self.id, 'view_type' : 'form', 'view_mode' : 'form', 'target' : 'new'} 


presupuesto_ejecucion_ing_contables()

