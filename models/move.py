# -*- coding: utf-8 -*-
##############################################################################
# Hereda el modulo res.parner y se agregan los campo para la localizacion colombiana
# Inherits res.parner module and add the field to the Colombian location
##############################################################################

import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import json
import logging

import datetime
import calendar
from datetime import datetime, timedelta, date
from openerp.http import request
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import time
import base64

try:
    import xlsxwriter
except ImportError:
    _logger.debug('Can not import xlsxwriter`.')

import logging

_logger = logging.getLogger(__name__)


class presupuesto_move(models.Model):

	_name = 'presupuesto.move'
	_inherit = ['mail.thread']

	def copy(self):

		default = {}
		default.update({
			'state': 'draft',
			'name': False,
			'move_id': False,
		})
		if 'date' not in default:
			default['date'] = time.strftime('%Y-%m-%d')
		return super(presupuesto_move, self).copy(default = default)	

	@api.multi
	def unlink(self):

		record = self

		presupuesto_move_read = self.read(['state'])
		obj_tc = self.env['presupuesto.move']
		unlink_ids = []

		for t in presupuesto_move_read:
			if t['state'] not in ('draft'):
				raise ValidationError(_('No puede suprimir un registro confirmado.'))
		

		if record.doc_type == 'ini':
			year = record.fiscal_year.id
			condition = [('doc_type', '!=', 'ini'),
									  ('id', '!=', record.id),
									  ('fiscal_year', '=', year)
									  ]

			ids = obj_tc.search(condition )

			if ids:
				raise ValidationError(_('No puede suprimir un presupuesto que ya tiene movimientos.'))
			#else:
			#	record.unlink()
		
		return super(presupuesto_move, self).unlink()

	@api.one
	def button_confirm(self):
		if  self.doc_type == 'ini':
			ingresos = 0
			for reg_ingreso in self.ingresos_ids:
				ingresos += reg_ingreso.ammount
			gastos = 0
			for reg_gasto in self.gastos_ids:
				gastos += reg_gasto.ammount
			if  ingresos != gastos:
				pass
				#raise ValidationError(_('El presupuesto debe tener igual monto de ingresos y de gastos para poderlo confirmar'))

		for rubro in self.line_id:
			if rubro._check_saldo() == False:
				raise ValidationError('El valor del movimiento no puede ser superior al saldo.')
				
		self._validate_move()

		if  self.doc_type == 'reg':
			cdp = self.env['presupuesto.move'].search([('name', '=', self.move_rel.name)])
			cdp.rp_associates_cdp += ' ' + self.name

		if  self.doc_type == 'pago':
			# Generar pago de la factura del proveedor
			# vals_pago_factura = {}
			# vals_pago_factura['journal_id'] = self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id
			# vals_pago_factura['journal_id'] = self.payment_journal_id.id

			# if self.move_rel.invoice_id and self.move_rel.invoice_id.amount_tax > self.move_rel.invoice_id.amount_untaxed:
			# 	factor_impuesto = (self.move_rel.invoice_id.amount_tax / self.move_rel.invoice_id.amount_untaxed)  
			# 	monto_con_impuesto = factor_impuesto * self.amount_total
			# else:
			# 	monto_con_impuesto = self.amount_total 
			# if self.move_rel.invoice_id and monto_con_impuesto > self.move_rel.invoice_id.residual:
			# 	raise ValidationError('El monto a pagar es mayor que la deuda de la factura')

			if self.move_rel.invoice_id and self.amount_total > self.move_rel.invoice_id.residual:
				raise ValidationError('El monto a pagar es mayor que la deuda de la factura')

			if self.voucher_id:

				if (self.voucher_id.amount != self.amount_total) or (self.voucher_id.payment_type != 'outbound') or (self.voucher_id.partner_type != 'supplier') or (self.voucher_id.partner_id != self.partner_id) :
					raise ValidationError('Los datos del comprobante contable difieren del pago presupuestal')
				self.voucher_id.write({'invoice_ids' : [(4, self.move_rel.invoice_id.id, None)]})
				self.voucher_id.post()			 

		self.write({'state':'confirm'})

		return 

	def button_void(self):
		documento = self.id
		doc_type = self.doc_type
		condicion = []
		if  doc_type == 'cdp':
			condicion = [('doc_type', 'in', ['reg','mod_cdp']), ('move_rel', '=', documento), ('state', 'in', ['draft','confirm'])]
			mensaje = 'No puede suprimir este CDP ya que esta siendo referido en algún registro presupuestal o en alguna modificación CDP.'
		if  doc_type == 'reg':
			condicion = [('doc_type', 'in', ['obl','mod_reg']), ('move_rel', '=', documento), ('state', 'in', ['draft','confirm'])]
			mensaje = 'No puede suprimir este registro presupuestal ya que esta siendo referida en alguna orden de pago o en alguna modificación RP.'
		if  doc_type == 'obl':
			condicion = [('doc_type', '=', 'pago'), ('move_rel', '=', documento), ('state', 'in', ['draft','confirm'])]
			mensaje = 'No puede suprimir esta orden de pago ya que esta siendo referida en algún pago.'
		if  doc_type == 'pago':
			condicion = [('move_rel', '=', documento), ('state', 'in', ['draft','confirm'])]
			mensaje = 'No puede suprimir este pago ya que esta siendo referido en otro documento.'
		if  doc_type == 'mod_cdp':
			condicion = [('move_rel', '=', self.move_rel.id), ('doc_type', '!=', 'mod_cdp'), ('state', 'in', ['draft','confirm'])]
			mensaje = 'No puede suprimir esta modificación de CDP ya que su CDP esta siendo utilizado en algún registro presupuestal.'
		if  doc_type == 'mod_reg':
			condicion = [('move_rel', '=', self.move_rel.id), ('doc_type', '!=', 'mod_reg'), ('state', 'in', ['draft','confirm'])]
			mensaje = 'No puede suprimir esta modificación de RP ya que su RP esta siendo utilizado en algún registro presupuestal.'
		ids = self.env['presupuesto.move'].search(condicion)

		if ids:
			raise ValidationError(_(mensaje))
		else:
			self.write({'state': 'void'})

		return 

	@api.one
	def button_cancel(self):
		return self.write({'state': 'draft'})   

	@api.one
	def button_rejected(self):
		return self.write({'state': 'rejected'}) 

	@api.onchange('date')
	def onchange_date(self):
		values = {}
		res = {}
		if not self.date:
			return res

		period_pool = self.sudo().env['account.period']
		search_periods = period_pool.with_context( account_period_prefer_normal=True ).find(self.date)


		period = search_periods[0]

		self.period_id = period


	@api.onchange('period_id')
	def onchange_period(self):
		values = {}
		res = {}
		if not self.period_id:
			return res
		year = self.period_id.fiscalyear_id.id


		self.fiscal_year = year

	# @api.onchange('move_rel')
	# def onchange_move_rel(self):
	# 	if self.move_rel:
	# 		if self.move_rel.state == 'draft':
	# 			n = self.move_rel.name
	# 			self.move_rel = False
	# 			return {'value':{},'warning':{'title':'warning','message':'El %s se encuentra en estado borrador, se debe confirmar para continuar' % ( n )}}


	@api.onchange('fiscal_year')
	def onchange_fiscal_year(self):
		values = {}
		res = {}
		if not self.fiscal_year:
			return res
		year = self.env['account.fiscalyear'].browse(self.fiscal_year.id)
		start = year.date_start
		stop = year.date_stop


		self.date_start = start
		self.date_stop = stop
		self.date = start

	@api.onchange('move_rel')
	def _onchange_move_rel(self):
		if self.move_rel:
			if self.move_rel.state == 'draft':
				n = self.move_rel.name
				self.move_rel = False
				return {'value':{},'warning':{'title':'warning','message':'El %s se encuentra en estado borrador, se debe confirmar para continuar' % ( n )}}

		if 	self.move_rel != False:
			rpre_moverubros = self.env['presupuesto.moverubros']
			cdp_moverubros = rpre_moverubros.search([('move_id.id', '=', self.move_rel.id)])
			lista_rubros = []
			move_type = self.doc_type
			if self.doc_type == 'mod_cdp':
				move_type = 'adi_cdp'
			if self.doc_type == 'mod_reg':
				move_type = 'adi_reg'
			# if self.doc_type == 'pago':				
			# 	for rubro in cdp_moverubros:
			# 		lista_rubros.append((0,0,{'move_id' : self.id , 'rubros_id' : rubro.rubros_id.id, 'mov_type' : move_type, 'date' : fields.Date.today(), 'period_id' : self.period_id.id, 'ammount' : rubro.ammount}))
			# else:
			for rubro in cdp_moverubros:
				lista_rubros.append((0,0,{'move_id' : self.id , 'rubros_id' : rubro.rubros_id.id, 'mov_type' : move_type, 'date' : fields.Date.today(), 'period_id' : self.period_id.id}))
			self.gastos_ids = lista_rubros
			if self.doc_type == 'pago':				
				for rubro_pago in self.gastos_ids:
					rubro_pago.ammount = rubro_pago.saldo_move

		self.description = self.move_rel.description
		self.partner_id = self.move_rel.partner_id

	@api.one
	@api.depends('gastos_ids')
	def _amount_total(self):
		res = {}
		total = 0.0
		for line in self.gastos_ids:
			total += line.ammount

		self.amount_total = total

	@api.one
	@api.depends('ingresos_ids')
	def _amount_total_ingresos(self):
		res = {}
		total = 0.0
		for line in self.ingresos_ids:
			total += line.ammount

		self.amount_total_ingresos = total

	# @api.one
	# # @api.depends('gastos_ids')
	# def _amount_available(self):
	# 	if type( self.id ) == int:
	# 		rec_moverel = self.env['presupuesto.move'].search([('move_rel.id', '=', self.id), ('state', '=', 'confirm')])
	# 		amount_used = 0.0
	# 		for moverel in rec_moverel:
	# 			if moverel.doc_type in ('mod_cdp','mod_reg'):
	# 				for rubro in moverel.gastos_ids:
	# 					if rubro.mov_type in ('adi_cdp','adi_reg'):
	# 						amount_used = amount_used - rubro.ammount
	# 					else:
	# 						amount_used = amount_used + rubro.ammount
	# 			else:
	# 				amount_used = amount_used + moverel.amount_total
						
	# 		self.amount_available = self.amount_total - amount_used

	@api.one
	# @api.depends('gastos_ids')
	def _amount_available(self):
		if type( self.id ) == int:
			rec_moverel = self.env['presupuesto.move'].search([('move_rel.id', '=', self.id), ('state', 'in', ['draft','confirm'])])
			amount_used = 0.0
			for moverel in rec_moverel:
				if moverel.doc_type in ('mod_cdp','mod_reg'):
					if moverel.state == 'confirm':
						for rubro in moverel.gastos_ids:
							if rubro.mov_type in ('adi_cdp','adi_reg'):
								amount_used = amount_used - rubro.ammount
							else:
								amount_used = amount_used + rubro.ammount
				else:
					amount_used = amount_used + moverel.amount_total
						
			amount_modi_total_rp = 0
			if self.doc_type == 'cdp':
				for moverel in rec_moverel:
					if moverel.doc_type == 'reg':
						rps = self.env['presupuesto.move'].search([('move_rel.id', '=', moverel.id), ('state', '=', 'confirm')])
						for rp in rps:
							if rp.doc_type == 'mod_reg':
								for rubro_rp in rp.gastos_ids:
									if rubro_rp.mov_type == 'adi_reg':
										amount_modi_total_rp += rubro_rp.ammount
									else:
										amount_modi_total_rp -= rubro_rp.ammount

			self.amount_available = self.amount_total - amount_used - amount_modi_total_rp

 	@api.one
	def _amount_cdp_adicion(self):
		if type( self.id ) == int:
			rec_moverel = self.env['presupuesto.move'].search([('move_rel.id', '=', self.id), ('state', '=', 'confirm')])
			amount_cdp_adicion = 0.0
			for moverel in rec_moverel:
				if moverel.doc_type == 'mod_cdp':
					for rubro in moverel.gastos_ids:
						if rubro.mov_type == 'adi_cdp':
							amount_cdp_adicion += rubro.ammount
						
			self.amount_cdp_adicion = amount_cdp_adicion

	@api.one
	def _amount_cdp_reduccion(self):
		if type( self.id ) == int:
			rec_moverel = self.env['presupuesto.move'].search([('move_rel.id', '=', self.id), ('state', '=', 'confirm')])
			amount_cdp_reduccion = 0.0
			for moverel in rec_moverel:
				if moverel.doc_type == 'mod_cdp':
					for rubro in moverel.gastos_ids:
						if rubro.mov_type == 'red_cdp':
							amount_cdp_reduccion += rubro.ammount
						
			self.amount_cdp_reduccion = amount_cdp_reduccion

	@api.model
	def create(self, vals):
		# Asignar secuencia según tipo de documento
		sequence_model = self.env['ir.sequence']

		if not vals.get('name'):
			if vals.get('doc_type')=='rec':
				vals['name'] = sequence_model.next_by_code('recaudo.sequence')
			elif vals.get('doc_type')=='cdp':
				vals['name'] = sequence_model.next_by_code('cdp.sequence')
			elif vals.get('doc_type')=='reg':
				vals['name'] = sequence_model.next_by_code('compromiso.sequence')
			elif vals.get('doc_type')=='obl':
				vals['name'] = sequence_model.next_by_code('obligacion.sequence')
			elif vals.get('doc_type')=='pago':
				vals['name'] = sequence_model.next_by_code('pago.sequence')
			elif vals.get('doc_type')=='ini':
				vals['name'] = sequence_model.next_by_code('inicial.sequence')
			elif vals.get('doc_type')=='mod':
				vals['name'] = sequence_model.next_by_code('modificacion.sequence')
			# elif vals.get('doc_type')=='var':
			# 	vals['name'] = sequence_model.next_by_code('modificaciones_cdp_rp.sequence')
			elif vals.get('doc_type')=='mod_cdp':
				vals['name'] = sequence_model.next_by_code('modificaciones_cdp.sequence')
			elif vals.get('doc_type')=='mod_reg':
				vals['name'] = sequence_model.next_by_code('modificaciones_reg.sequence')
			else :
				vals['name'] = "/"

		invoice = self.env['account.invoice'].browse(vals.get('invoice_id'))
		vals['amount_residual'] = invoice.residual

		new_move = super(presupuesto_move, self).create(vals)
		if vals.get('doc_type') != 'ini':
			new_move._validate_move()

		return new_move

	def write(self,vals):
		if self.doc_type == 'obl' and self.state == 'draft':
 			if vals.get('invoice_id'):
 				invoice = self.env['account.invoice'].browse(vals.get('invoice_id'))
				vals['amount_residual'] = invoice.residual

		res = super(presupuesto_move, self).write(vals)
		if self.doc_type != 'ini':
			self._validate_move()

 	 	return res

 	def _validate_move(self):
# 		if  self.amount_total <= 0:
# 			raise ValidationError('El monto de este documento debe ser mayor que cero')

 		if self.doc_type == 'obl':
			if self.invoice_id and self.amount_total > self.amount_residual:   
				raise ValidationError('El monto de la Orden de Pago no debe superar el monto sin impuesto de la factura')

		if  self.doc_type in ['reg','obl','pago','mod_cdp','mod_reg']:
			if self.move_rel.date > self.date:
				raise ValidationError(_('No puede grabar o confirmar esta transacción porque la fecha del documento relacionado es mayor que la fecha de este documento'))

		if  self.doc_type == 'pago' and self.voucher_id and self.amount_total > self.voucher_id.amount:
				raise ValidationError(_('No puede grabar o confirmar esta transacción porque el monto de este pago supera al monto del comprobante'))

		# if  self.doc_type == 'mod_cdp':
		# 	cdp = self.move_rel
		# 	for rubro in self.line_id:
		# 		if rubro.mov_type == 'adi_cdp':
		# 			for rubro_cdp in cdp.line_id:
		# 				rubro_cdp._saldo_move(True)
		# 				if rubro_cdp.rubros_id.id == rubro.rubros_id.id and rubro_cdp.saldo_move < rubro.ammount:
		# 					raise ValidationError(_('El monto a adicionar no puede superar el monto disponible del presupuesto anual'))

		if  self.doc_type == 'mod_cdp':
			for rubro in self.line_id:
				if rubro.mov_type == 'adi_cdp' and rubro.saldo_move < rubro.ammount:
					raise ValidationError(_('El monto a adicionar no puede superar el monto disponible del presupuesto anual'))

		# if  self.doc_type == 'mod_reg':
		# 	cdp = self.move_rel
		# 	for rubro in self.line_id:
		# 		if rubro.mov_type == 'adi_reg':
		# 			for rubro_cdp in cdp.line_id:
		# 				rubro_cdp._saldo_move(True)
		# 				if rubro_cdp.rubros_id.id == rubro.rubros_id.id and (rubro_cdp.saldo_move - rubro.saldo_move) < rubro.ammount:
		# 					raise ValidationError(_('El monto a adicionar no puede superar el monto disponible del CDP'))

		if  self.doc_type == 'mod_reg':
			for rubro in self.line_id:
				if rubro.mov_type == 'adi_reg' and rubro.saldo_move < rubro.ammount:
					raise ValidationError(_('El monto a adicionar no puede superar el monto disponible del CDP'))

	def print_cdp(self):
		res = self.env['report'].get_action(self, 'l10n_co_budget.report_cdp')
		return res

	def print_rp(self):
		res = self.env['report'].get_action(self, 'l10n_co_budget.report_rp')
		return res  

	def print_mod_cdp(self):
		res = self.env['report'].get_action(self, 'l10n_co_budget.report_mod_cdp')
		return res 

	def print_mod_rp(self):
		res = self.env['report'].get_action(self, 'l10n_co_budget.report_mod_rp')
		return res 

	def print_orden_pago(self):
		res = self.env['report'].get_action(self, 'l10n_co_budget.report_orden_pago')
		return res  

	def print_pago_presupuestal(self):
		res = self.env['report'].get_action(self, 'l10n_co_budget.report_pago_presupuestal')
		return res

	def print_recaudos(self):
		res = self.env['report'].get_action(self, 'l10n_co_budget.report_recaudos')
		return res 

	def print_modificacion_ingresos_gastos(self):
		res = self.env['report'].get_action(self, 'l10n_co_budget.report_modificaciones_ingresos_gastos')
		return res 

	def print_presupuesto_anual(self):
		res = self.env['report'].get_action(self, 'l10n_co_budget.report_presupuesto_anual')
		return res

	@api.onchange('contract_id')
	def get_partner_contract(self):
		if self.sudo().contract_id.employee_id.resource_id.user_id.partner_id: 
			self.partner_id = self.sudo().contract_id.employee_id.resource_id.user_id.partner_id

	@api.onchange('invoice_id')
	def _get_partner_account_invoice(self):
		if self.invoice_id.partner_id:
			self.partner_id = self.invoice_id.partner_id 
		self.amount_residual = self.invoice_id.residual
	
	@api.onchange('partner_id')
	def reset_contract_id_and_invoice_id(self):
		return_dict = {}
		if self.doc_type == 'reg':
			if self.sudo().partner_id != self.sudo().contract_id.employee_id.resource_id.user_id.partner_id:
				if self.sudo().partner_id.id == False:
					dict_dominio = {'contract_id' : "[('id','>',0)]"}
				else:					
					dict_dominio = {'contract_id' : "[('employee_id.resource_id.user_id.partner_id', '=', partner_id)]"} 
				dict_valores = {'contract_id' : None}
				return_dict['value'] = dict_valores
				return_dict['domain'] = dict_dominio
		if self.doc_type == 'obl':
			if self.sudo().partner_id != self.sudo().invoice_id.partner_id:
				if self.sudo().partner_id.id == False:
					dict_dominio = {'invoice_id' : "[('id','>',0), ('state', '=', 'open'), ('date_invoice', '<=', date), ('journal_id', '=', 2)]"}
				else:
					dict_dominio = {'invoice_id' : "[('partner_id', '=', partner_id), ('state', '=', 'open'), ('date_invoice', '<=', date), ('journal_id', '=', 2)]"} 
				dict_valores = {'invoice_id' : None}
				return_dict['value'] = dict_valores
				return_dict['domain'] = dict_dominio

		return return_dict

	def export_excel_budget(self):
		workbook = xlsxwriter.Workbook('/tmp/presupuesto_anual.xlsx')
		worksheet_ingresos = workbook.add_worksheet()
		worksheet_gastos = workbook.add_worksheet()
		format_company = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left', })
		format_titulo = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
		format_cabecera = workbook.add_format({'bold': True, 'font_size': 12, 'border': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': 'gray'})
		format_celda_str = workbook.add_format({'font_size': 12, 'border': True})
		format_celda_num = workbook.add_format({'font_size': 12, 'border': True, 'num_format': '#,##0.00'})
		format_celda_num_tol = workbook.add_format({'bold': True,'font_size': 12, 'border': True, 'num_format': '#,##0.00'})
		format_celda_str_tol = workbook.add_format({'bold': True,'font_size': 12, 'border': True, 'align': 'right'})
		company = self.env.user.partner_id.company_id.name
		worksheet_ingresos.merge_range('A1:D1', company, format_company)
		titulo_hoja = u'Presupuesto anual de ingresos del año fiscal ' + self.fiscal_year.name
		worksheet_ingresos.merge_range('A2:N2', titulo_hoja, format_titulo)
		worksheet_ingresos.name = 'Ingresos'
		worksheet_gastos.merge_range('A1:D1', company, format_company)
		titulo_hoja = u'Presupuesto anual de gastos del año fiscal ' + self.fiscal_year.name
		worksheet_gastos.merge_range('A2:N2', titulo_hoja, format_titulo)
		worksheet_gastos.name = 'Gastos'
		# Ingresos
		row = 4
		worksheet_ingresos.write(row, 0, 'Rubro', format_cabecera)
		worksheet_ingresos.write(row, 1, 'Nombre', format_cabecera)
		worksheet_ingresos.write(row, 2, 'Tipo', format_cabecera)
		worksheet_ingresos.write(row, 3, 'Valor', format_cabecera)
		worksheet_ingresos.write(row, 4, 'Enero', format_cabecera)
		worksheet_ingresos.write(row, 5, 'Febrero', format_cabecera)
		worksheet_ingresos.write(row, 6, 'Marzo', format_cabecera)
		worksheet_ingresos.write(row, 7, 'Abril', format_cabecera)
		worksheet_ingresos.write(row, 8, 'Mayo', format_cabecera)
		worksheet_ingresos.write(row, 9, 'Junio', format_cabecera)
		worksheet_ingresos.write(row, 10, 'Julio', format_cabecera)
		worksheet_ingresos.write(row, 11, 'Agosto', format_cabecera)
		worksheet_ingresos.write(row, 12, 'Septiembre', format_cabecera)
		worksheet_ingresos.write(row, 13, 'Octubre', format_cabecera)
		worksheet_ingresos.write(row, 14, 'Noviembre', format_cabecera)
		worksheet_ingresos.write(row, 15, 'Diciembre', format_cabecera)
		worksheet_ingresos.set_column('A:A',15)
		worksheet_ingresos.set_column('B:B',40)
		worksheet_ingresos.set_column('D:P',20)
		dict_mov_type = {'ini':'Inicial','adi':'Adición','red':'Reducción','cre':'Crédito',
			'cont':'Contracrédito','rec':'Recaudo','cdp':'CDP','reg':'Compromiso','obl':'Obligación',
			'pago':'Pago','adi_cdp':'Adición CDP','red_cdp':'Reducción CDP',
			'adi_reg':'Adición RP','red_reg':'Reducción RP'}
		presupuesto_ingresos = self.ingresos_ids
		ingresos = 0
		for ingreso in presupuesto_ingresos:
			row += 1
			ingresos += ingreso.ammount
			worksheet_ingresos.write(row, 0, ingreso.rubros_id.code, format_celda_str)
			worksheet_ingresos.write(row, 1, ingreso.rubros_id.name, format_celda_str)
			worksheet_ingresos.write(row, 2, dict_mov_type[ingreso.mov_type], format_celda_str)
			worksheet_ingresos.write(row, 3, ingreso.ammount, format_celda_num)
			worksheet_ingresos.write(row, 4, ingreso.enero, format_celda_num)
			worksheet_ingresos.write(row, 5, ingreso.febrero, format_celda_num)
			worksheet_ingresos.write(row, 6, ingreso.marzo, format_celda_num)
			worksheet_ingresos.write(row, 7, ingreso.abril, format_celda_num)
			worksheet_ingresos.write(row, 8, ingreso.mayo, format_celda_num)
			worksheet_ingresos.write(row, 9, ingreso.junio, format_celda_num)
			worksheet_ingresos.write(row, 10, ingreso.julio, format_celda_num)
			worksheet_ingresos.write(row, 11, ingreso.agosto, format_celda_num)			
			worksheet_ingresos.write(row, 12, ingreso.septiembre, format_celda_num)
			worksheet_ingresos.write(row, 13, ingreso.octubre, format_celda_num)
			worksheet_ingresos.write(row, 14, ingreso.noviembre, format_celda_num)
			worksheet_ingresos.write(row, 15, ingreso.diciembre, format_celda_num)
		row += 1
		celda = 'B' + str(row+1) + ':C' + str(row+1)
		worksheet_ingresos.merge_range(celda, 'Total ingresos:', format_celda_str_tol)
		worksheet_ingresos.write(row, 3, ingresos, format_celda_num_tol)
		# Gastos
		row = 4
		worksheet_gastos.write(row, 0, 'Rubro', format_cabecera)
		worksheet_gastos.write(row, 1, 'Nombre', format_cabecera)
		worksheet_gastos.write(row, 2, 'Tipo', format_cabecera)
		worksheet_gastos.write(row, 3, 'Valor', format_cabecera)
		worksheet_gastos.write(row, 4, 'Enero', format_cabecera)
		worksheet_gastos.write(row, 5, 'Febrero', format_cabecera)
		worksheet_gastos.write(row, 6, 'Marzo', format_cabecera)
		worksheet_gastos.write(row, 7, 'Abril', format_cabecera)
		worksheet_gastos.write(row, 8, 'Mayo', format_cabecera)
		worksheet_gastos.write(row, 9, 'Junio', format_cabecera)
		worksheet_gastos.write(row, 10, 'Julio', format_cabecera)
		worksheet_gastos.write(row, 11, 'Agosto', format_cabecera)
		worksheet_gastos.write(row, 12, 'Septiembre', format_cabecera)
		worksheet_gastos.write(row, 13, 'Octubre', format_cabecera)
		worksheet_gastos.write(row, 14, 'Noviembre', format_cabecera)
		worksheet_gastos.write(row, 15, 'Diciembre', format_cabecera)
		worksheet_gastos.set_column('A:A',15)
		worksheet_gastos.set_column('B:B',40)
		worksheet_gastos.set_column('D:P',20)
		presupuesto_gastos = self.gastos_ids
		gastos = 0
		for gasto in presupuesto_gastos:
			row += 1
			gastos += gasto.ammount
			worksheet_gastos.write(row, 0, gasto.rubros_id.code, format_celda_str)
			worksheet_gastos.write(row, 1, gasto.rubros_id.name, format_celda_str)
			worksheet_gastos.write(row, 2, dict_mov_type[gasto.mov_type], format_celda_str)
			worksheet_gastos.write(row, 3, gasto.ammount, format_celda_num)
			worksheet_gastos.write(row, 4, gasto.enero, format_celda_num)
			worksheet_gastos.write(row, 5, gasto.febrero, format_celda_num)
			worksheet_gastos.write(row, 6, gasto.marzo, format_celda_num)
			worksheet_gastos.write(row, 7, gasto.abril, format_celda_num)
			worksheet_gastos.write(row, 8, gasto.mayo, format_celda_num)
			worksheet_gastos.write(row, 9, gasto.junio, format_celda_num)
			worksheet_gastos.write(row, 10, gasto.julio, format_celda_num)
			worksheet_gastos.write(row, 11, gasto.agosto, format_celda_num)			
			worksheet_gastos.write(row, 12, gasto.septiembre, format_celda_num)
			worksheet_gastos.write(row, 13, gasto.octubre, format_celda_num)
			worksheet_gastos.write(row, 14, gasto.noviembre, format_celda_num)
			worksheet_gastos.write(row, 15, gasto.diciembre, format_celda_num)
		row += 1
		celda = 'B' + str(row+1) + ':C' + str(row+1)
		worksheet_gastos.merge_range(celda, 'Total gastos:', format_celda_str_tol)
		worksheet_gastos.write(row, 3, gastos, format_celda_num_tol)
		workbook.close()

		archivo_excel = open('/tmp/presupuesto_anual.xlsx','rb')
		salida = archivo_excel.read()
		archivo_excel.close()

		self.excel_file_name = '/tmp/presupuesto_anual.xlsx'
		self.excel_file = base64.b64encode(salida)

		return
 

	# @api.one
	# def _get_apunte_contable(self):
	# 	self.account_move_line_ids = self.invoice_id.move_id.line_ids 

	name = fields.Char('Documento N°', select=1, size=32, readonly=True)
	doc_type = fields.Selection([
							   ('ini', 'Inicial'),
							   ('mod', 'Modificacón'),
							   ('rec', 'Recaudo'),
							   ('cdp', 'CDP'),
							   ('reg', 'Compromiso'),
							   ('obl', 'Obligación'),
							   ('pago', 'Pago'),
							   # ('var', 'Modificación CDP y RP')
							   ('mod_cdp', 'Modificación CDP'),
							   ('mod_reg', 'Modificación RP')], 'Tipo', select=True, required=True, states={'confirm': [('readonly', True)]})

	fiscal_year = fields.Many2one('account.fiscalyear', 'Año fiscal', select=True, required=True, states={'confirm': [('readonly', True)]})
	period_id = fields.Many2one('account.period', 'Periodo', required=True)
	company_id = fields.Many2one('res.company', 'Company', required=True, default = lambda self: self.env.user.company_id.id)
	date_start = fields.Date('Desde')
	date_stop = fields.Date('Hasta')
	date = fields.Date('Fecha', required=True, states={'confirm': [('readonly', True)], 'void': [('readonly', True)]})
	partner_id = fields.Many2one('res.partner', 'Tercero', ondelete='restrict', states={'confirm': [('readonly', True)], 'void': [('readonly', True)]})
	move_rel = fields.Many2one('presupuesto.move', 'Documento relacionado',ondelete='restrict', states={'confirm': [('readonly', True)], 'void': [('readonly', True)]})
	description = fields.Text('Descripción', size=1500, required=True, states={'confirm': [('readonly', True)], 'void': [('readonly', True)]})
	voucher_id = fields.Many2one('account.payment', 'Comprobante',ondelete='restrict', states={'confirm': [('readonly', True)], 'void': [('readonly', True)]})
	contract_id = fields.Many2one('hr.contract', 'Contrato', ondelete='restrict', states={'confirm': [('readonly', True)], 'void': [('readonly', True)]})
	invoice_id = fields.Many2one('account.invoice', 'Factura', ondelete='restrict', states={'confirm': [('readonly', True)], 'void': [('readonly', True)]})
	payslip_id = fields.Many2one('hr.payslip', 'Nómina', ondelete='restrict', states={'confirm': [('readonly', True)], 'void': [('readonly', True)]})
	line_id = fields.One2many('presupuesto.moverubros', 'move_id', 'Entries', states={'confirm': [('readonly', True)], 'void': [('readonly', True)]})

	ingresos_ids = fields.One2many('presupuesto.moverubros', 'move_id', 'Rubros', states={'confirm': [('readonly', True)], 'void': [('readonly', True)]}, domain=[('rubros_id.rubro_tipo', '=', 'I', )], ondelete = 'cascade')

	gastos_ids = fields.One2many('presupuesto.moverubros', 'move_id', 'Rubros', states={'confirm': [('readonly', True)], 'void': [('readonly', True)]},
								   domain=[('rubros_id.rubro_tipo', '=', 'G')], ondelete = 'cascade' )
								    
	state = fields.Selection([
							   ('draft', 'Borrador'),
							   ('confirm', 'Confirmado'),
							   ('rejected', 'Rechazado'),
							   ('void', 'Anulado'),
							   ], 'Status', select=True, default = 'draft')

	amount_total = fields.Float(string = 'Valor Total', compute = '_amount_total', store = True)
	amount_to_text_total =  fields.Char(string='Valor en letras')
	amount_available = fields.Float(string = 'Valor Total', compute = '_amount_available', store = False)

	rubros_move_rel = fields.Char('rubros_originales') 

	excel_file_name = fields.Char('Nombre archivo excel')
	excel_file = fields.Binary('Archivo excel generado:', readonly='True')
	rp_associates_cdp = fields.Char('Registros presupuestales', default = ' ')
	currency_id = fields.Many2one('res.currency', related = 'invoice_id.currency_id')
	amount_invoice = fields.Monetary('Monto de factura con impuesto', related = 'invoice_id.amount_total')
	amount_tax = fields.Monetary('Monto de los impuestos', related = 'invoice_id.amount_tax')
	amount_untaxed = fields.Monetary('Monto de factura sin impuestos', related = 'invoice_id.amount_untaxed')
	amount_residual = fields.Monetary('Monto de factura sin impuestos')
	amount_tax_obligacion = fields.Monetary('Monto de los impuestos de la orde de pago', related = 'move_rel.invoice_id.amount_tax')
	tax_line_ids = fields.One2many('account.invoice.tax', related = 'invoice_id.tax_line_ids')
	account_move_line_ids = fields.One2many('account.move.line', related = 'invoice_id.move_id.line_ids')
	#account_move_line_ids = fields.One2many('account.move.line', 'move_id', compute = '_get_apunte_contable')
	amount_total_ingresos = fields.Float(string = 'Valor Total', compute = '_amount_total_ingresos', store = True)

	amount_cdp_adicion = fields.Float(string = 'Total adiciones al CDP', compute = '_amount_cdp_adicion', store = False)
	amount_cdp_reduccion = fields.Float(string = 'Total reducciones al CDP', compute = '_amount_cdp_reduccion', store = False)

	id_externo = fields.Char(string = 'Identificador externo del origen de la importación')
