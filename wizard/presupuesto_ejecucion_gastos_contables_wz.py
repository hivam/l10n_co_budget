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


class presupuesto_ejecucion_gastos_contables(models.TransientModel):
	_name = "presupuesto.ejecucion.gastos.contables"
	_description = "Ejecucion de Gastos Contables"

	chart_rubros_id = fields.Many2one('presupuesto.rubros', 'Plan de Rubros', required=True, domain = [('parent_id','=', False)], default = lambda self: self._get_rubros(), ondelete = 'cascade')
	fiscalyear_id =  fields.Many2one('account.fiscalyear', u'Año fiscal', select=True, required=True, default = lambda self: self._get_fiscalyear())
	company_id = fields.Many2one('res.company', 'Company', related = 'chart_rubros_id.company_id')
	period_from = fields.Many2one('account.period', 'Periodo inicial', required=True)
	period_to =  fields.Many2one('account.period', 'Periodo final', required=True)
	period_ant =  fields.Many2one('account.period', 'Periodo anterior')

	data_ids = fields.One2many('presupuesto.ejecucion.gastos.contables.report', 'active_id', 'Records')
	excel_file_name = fields.Char('Nombre archivo excel')
	excel_file = fields.Binary('Archivo excel generado:', readonly='True')

	
	def _get_rubros(self):
		rubros = self.env['presupuesto.rubros'].search([('parent_id', '=', False), ('company_id', '=', self.env.user.company_id.id)], limit=1)
		return rubros and rubros[0] or False

	
	def _get_fiscalyear(self):
		context = self.env.context

		now = time.strftime('%Y-%m-%d')
		company_id = False
		ids = context.get('active_ids', [])
		if ids and context.get('active_model') == 'presupuesto.rubros':

			company_id = self.env['presupuesto.rubros'].browse(ids[0]).company_id.id
		else:  # use current company id
			company_id = self.env.user.company_id.id

		domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
		fiscalyears = self.env['account.fiscalyear'].search(domain)
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
	def create_ejecucion_gastos_contables_excel(self):

		datos = self.env['presupuesto.util'].sql({'rubro_tipo' : 'G'}, {
			'active_model' : 'presupuesto.ejecucion.gastos.contables',
			'active_id' : self.id
		})
		if datos:
			datos = datos[ 0 ]

			self.env.cr.execute('delete from presupuesto_ejecucion_gastos_contables_report where active_id = %s' % ( self.id ))

			sql = 'insert into presupuesto_ejecucion_gastos_contables_report(active_id, rubro_codigo, rubro_nombre, rubro_nivel, rubro_codigo_cta_contable, rubro_nombre_cta_contable, obligacion_cta_mes_actual, obligacion_cta_acumulado, adiciones, reducciones, creditos, contracreditos, apropiacion_definitiva, ejecutado_anterior, ejecutado_mes, total_ejecutado, saldo_por_ejecutar, porcentaje, cdp_mes_anterior, cdp_mes_actual, cdp_acumulado, apropiacion_disponible, registro_mes_anterior, registro_mes_actual, registro_acumulado, comprometer, obligacion_mes_anterior, obligacion_mes_actual, obligacion_acumulado, por_obligar, pago_mes_anterior, pago_mes_actual, pago_acumulado, por_pagar) values'
			values = []
			for dato in datos:
				dato.update({
					'active_id' : self.id
				})
				values.append("(%(active_id)s, '%(rubro_codigo)s', '%(rubro_nombre)s', '%(rubro_nivel)s', '%(rubro_codigo_cta_contable)s', '%(rubro_nombre_cta_contable)s', '%(obligacion_cta_mes_actual)s', '%(obligacion_cta_acumulado)s', '%(adiciones)s', '%(reducciones)s', '%(creditos)s', '%(contracreditos)s', '%(apropiacion_definitiva)s', '%(ejecutado_anterior)s', '%(ejecutado_mes)s', '%(total_ejecutado)s', '%(saldo_por_ejecutar)s', '%(porcentaje)s', '%(cdp_mes_anterior)s', '%(cdp_mes_actual)s', '%(cdp_acumulado)s', '%(apropiacion_disponible)s', '%(registro_mes_anterior)s', '%(registro_mes_actual)s', '%(registro_acumulado)s', '%(comprometer)s', '%(obligacion_mes_anterior)s', '%(obligacion_mes_actual)s', '%(obligacion_acumulado)s', '%(por_obligar)s', '%(pago_mes_anterior)s', '%(pago_mes_actual)s', '%(pago_acumulado)s', '%(por_pagar)s')" % dato  )

			sql = sql + ','.join( values )	

			_logger.info( sql )

			self.env.cr.execute( sql )

		workbook = xlsxwriter.Workbook('/tmp/presupuesto_ejecucion_gastos_contables.xlsx')
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
		worksheet.set_column('F:T',20)
		company = self.env.user.partner_id.company_id.name
		rec_gastos = self.sudo().env['presupuesto.ejecucion.gastos.contables.report'].search([('active_id', '=', self.id)])
		worksheet.merge_range('A1:D1', company, format_company)
		worksheet.merge_range('A3:M3', u'Ejecución de Gastos Contables', format_titulo)
		worksheet.merge_range('A4:A5', 'Rubro', format_cabecera)
		worksheet.merge_range('B4:B5', 'Nombre', format_cabecera)
		worksheet.merge_range('C4:C5', 'N', format_cabecera)
		worksheet.merge_range('D4:D5', 'Cuenta\ncontable', format_cabecera)
		worksheet.merge_range('E4:E5', 'Nombre', format_cabecera)
		worksheet.merge_range('F4:G4', u'Obligación Rubro', format_cabecera)
		worksheet.merge_range('H4:I4', u'Obligación cuenta contable', format_cabecera)
		worksheet.merge_range('J4:K4', 'Pago', format_cabecera)
		worksheet.merge_range('L4:M4', 'Cta. x pagar', format_cabecera)
		row = 4
		worksheet.write(row, 5, 'MES', format_cabecera)
		worksheet.write(row, 6, 'ACUM', format_cabecera)
		worksheet.write(row, 7, 'MES', format_cabecera)
		worksheet.write(row, 8, 'ACUM', format_cabecera)
		worksheet.write(row, 9, 'MES', format_cabecera)
		worksheet.write(row, 10, 'ACUM', format_cabecera)
		worksheet.write(row, 11, 'MES', format_cabecera)
		worksheet.write(row, 12, 'ACUM', format_cabecera)
		row = 5
		for gasto in rec_gastos:
			worksheet.write(row, 0, gasto.rubro_codigo, format_celda_str)
			worksheet.write(row, 1, gasto.rubro_nombre, format_celda_str)
			worksheet.write(row, 2, gasto.rubro_nivel, format_celda_str)
			worksheet.write(row, 3, gasto.rubro_codigo_cta_contable, format_celda_str)
			worksheet.write(row, 4, gasto.rubro_nombre_cta_contable, format_celda_str)
			worksheet.write(row, 5, gasto.obligacion_mes_actual, format_celda_num)
			worksheet.write(row, 6, gasto.obligacion_acumulado, format_celda_num)
			worksheet.write(row, 7, gasto.obligacion_cta_mes_actual, format_celda_num)
			worksheet.write(row, 8, gasto.obligacion_cta_acumulado, format_celda_num)
			worksheet.write(row, 9, gasto.pago_mes_actual, format_celda_num)
			worksheet.write(row, 10, gasto.pago_acumulado, format_celda_num)
			worksheet.write(row, 11, gasto.obligacion_mes_actual - gasto.pago_mes_actual, format_celda_num)
			worksheet.write(row, 12, gasto.obligacion_acumulado - gasto.pago_acumulado, format_celda_num)
			row += 1
			col = 0
		workbook.close()
		archivo_excel = open('/tmp/presupuesto_ejecucion_gastos_contables.xlsx','rb')
		salida = archivo_excel.read()
		archivo_excel.close()

		self.excel_file_name = 'presupuesto_ejecucion_gastos_contables.xlsx'
		self.excel_file = base64.b64encode(salida)

		return {'type' : 'ir.actions.act_window', 'res_model' : self._name, 'res_id' : self.id, 'view_type' : 'form', 'view_mode' : 'form', 'target' : 'new'} 

presupuesto_ejecucion_gastos_contables()
 