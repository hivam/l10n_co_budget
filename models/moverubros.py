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

import logging

_logger = logging.getLogger(__name__)


class presupuesto_moverubros(models.Model):
	_name = "presupuesto.moverubros"
	_rec_name = 'rubros_id'


	@api.onchange('move_id')
	def onchange_move_id(self):
		values = {}
		res = {}

		if not self.move_id:
			return res

		doc = self.move_id.doc_type
		if doc == 'ini':
			tipo = 'ini'
		elif doc == 'rec':
			tipo = 'rec'
		elif doc == 'cdp':
			tipo = 'cdp'
		elif doc == 'reg':
			tipo = 'reg'
		elif doc == 'obl':
			tipo = 'obl'
		elif doc == 'pago':
			tipo = 'pago'
		# elif doc == 'var':
		# 	tipo = 'var_adi'
		elif doc == 'mod_cdp':
			tipo = 'adi_cdp'
		elif doc == 'mod_reg':
			tipo = 'adi_reg'

		_logger.info("el tipo")
		_logger.info( tipo )

		self.mov_type = tipo

	# @api.one
	# @api.depends('saldo_move')
	# def _saldo_move(self, cdp=False):
	# 	res = {}
	# 	move_saldo = 0
	# 	obj_tc = self.env['presupuesto.moverubros']
	# 	record = self

	# 	_logger.info("testtt")
	# 	_logger.info( self.id )
	# 	_logger.info( type( self.id ) )

	# 	tipo = record.mov_type
	# 	rubro = record.rubros_id.id
	# 	moverel = record.move_id.move_rel.id
	# 	year = record.move_id.fiscal_year.id
	# 	tipo_doc = record.move_id.doc_type

	# 	conditions = [('rubros_id', '=', rubro),
	# 		('move_id.state', '=', 'confirm'),
	# 		('move_id.fiscal_year', '=', year)
	# 	]
	# 	if type( self.id ) == int and cdp == False:
	# 		conditions.append( ('id', '<', self.id) )

	# 	ids = obj_tc.search(conditions)

	# 	if tipo == "cdp" or tipo == "rec" or tipo_doc == 'mod':
	# 		move_saldo = saldo_resta = saldo_suma = 0.0
	# 		for move in ids:
	# 			if move.mov_type == 'ini' or move.mov_type == 'adi' or move.mov_type == 'cre' or move.mov_type == 'rec_cdp':
	# 				saldo_suma += move.ammount
	# 			if move.mov_type == 'red' or move.mov_type == 'cont' or move.mov_type == 'cdp' or move.mov_type == 'rec' or move.mov_type == 'adi_cdp':
	# 				saldo_resta += move.ammount
	# 			move_saldo = saldo_suma - saldo_resta

		
	# 	if tipo == "reg" or tipo == "obl" or tipo == "pago" or tipo_doc == "mod_cdp" or tipo_doc == "mod_reg":
	# 		move_saldo = move_val = saldo_rel = saldo_modi_rp = 00.0
	# 		for move in ids:
	# 			if move.move_id.id == moverel:
	# 				saldo_rel += move.ammount
	# 			if move.move_id.move_rel.id == moverel:
	# 				if move.mov_type in ('adi','adi_cdp','adi_reg'):
	# 					saldo_rel += move.ammount
	# 				else:
	# 					saldo_rel -= move.ammount

	# 			if move.move_id.move_rel.id == moverel and move.move_id.doc_type == 'reg':
	# 				for move_rp in ids:						
	# 					if move_rp.move_id.move_rel.id == move.move_id.id:
	# 						if move_rp.mov_type in ('adi','adi_cdp','adi_reg'):
	# 							saldo_modi_rp -= move_rp.ammount
	# 						else:
	# 							saldo_modi_rp += move_rp.ammount

	# 			move_saldo = saldo_rel + saldo_modi_rp

	# 	self.saldo_move = move_saldo
	# 	return self.saldo_move

	# @api.one
	# @api.onchange('mov_type')
	# def _move_type(self):
	# 	#self._saldo_move()
	# 	print ''
	# 	print 'Paso por aquí'
	# 	print 'saldo move onchange', self.saldo_move
	# 	print ''

	@api.one
	@api.depends('saldo_move')
	def _saldo_move(self, cdp=False):
		_logger.info("testtt")
		_logger.info( self.id )
		_logger.info( type( self.id ) )

		# if self.move_id.state != 'draft':
		# 	return

		year = self.move_id.fiscal_year.id
		formulado = 0.0
		utilizado = 0.0

		# Formualdo Modificación del presupuesto o CDP o Adición CDP 
		if self.move_id.doc_type == 'mod' or \
			self.move_id.doc_type == 'cdp' or \
			(self.move_id.doc_type == 'mod_cdp' and self.mov_type == 'adi_cdp') or \
			self.move_id.doc_type == 'rec':
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
			('move_id.fiscal_year', '=', year),('mov_type', 'in', ['ini','adi','red','cre','cont','rec']), ('move_id.name', '!=', self.move_id.name)]
			recursos = self.env['presupuesto.moverubros'].search(conditions)
			for recurso in recursos:
				if recurso.mov_type == 'ini' or recurso.mov_type == 'adi' or recurso.mov_type == 'cre':
					formulado += recurso.ammount
				if recurso.mov_type == 'red' or recurso.mov_type == 'cont' or recurso.mov_type == 'rec':
					formulado -= recurso.ammount

		# Formulado Reducción CDP o Registro presupuestal o Adición registro presupuestal
		if (self.move_id.doc_type == 'mod_cdp' and self.mov_type == 'red_cdp') or \
			self.move_id.doc_type == 'reg' or \
			(self.move_id.doc_type == 'mod_reg' and self.mov_type == 'adi_reg'):
			# Se obtiene formulado del CDP
			if self.mov_type != 'adi_reg':
			 	move_rel = self.move_id.move_rel.id
			else:
			 	move_rel = self.move_id.move_rel.move_rel.id
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),  
			('move_id.fiscal_year', '=', year),('mov_type', '=', 'cdp'),  
			('move_id.id', '=', move_rel)]
			formulado = self.env['presupuesto.moverubros'].search(conditions).ammount
			# Se obtiene las modificaciones al CDP
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
			('move_id.fiscal_year', '=', year),('mov_type', 'in', ['adi_cdp','red_cdp']),
			('move_id.move_rel.id', '=', move_rel), ('move_id.name', '!=', self.move_id.name)]
			# if type(self.id) == int:
			# 	conditions.append(('id', '!=', self.id))
			recursos = self.env['presupuesto.moverubros'].search(conditions)					
			for recurso in recursos:
				if recurso.mov_type == 'adi_cdp':
					formulado += recurso.ammount
				if recurso.mov_type == 'red_cdp':
					formulado -= recurso.ammount

		# Formulado Reducción Registro presupuestal o Obligación 
		if (self.move_id.doc_type == 'mod_reg' and self.mov_type == 'red_reg') or \
			self.move_id.doc_type == 'obl':
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),  
			('move_id.fiscal_year', '=', year),('mov_type', '=', 'reg'),
			('move_id.id', '=',  self.move_id.move_rel.id)]
			formulado = self.env['presupuesto.moverubros'].search(conditions).ammount
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
			('move_id.fiscal_year', '=', year),('mov_type', 'in', ['adi_reg','red_reg']),
			('move_id.move_rel.id', '=', self.move_id.move_rel.id), ('move_id.name', '!=', self.move_id.name)]
			# if type(self.id) == int:
			# 	conditions.append(('id', '!=', self.id))
			recursos = self.env['presupuesto.moverubros'].search(conditions)					
			for recurso in recursos:
				if recurso.mov_type == 'adi_reg':
					formulado += recurso.ammount
				if recurso.mov_type == 'red_reg':
					formulado -= recurso.ammount

		# Pago formulado
		if self.move_id.doc_type == 'pago':
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
			('move_id.fiscal_year', '=', year),('mov_type', '=', 'obl'),
			('move_id.id', '=', self.move_id.move_rel.id)]
			formulado = self.env['presupuesto.moverubros'].search(conditions).ammount

		# Utilizado Modificación del presupuesto CDP o Adición CDP 
		if self.move_id.doc_type == 'mod' or \
			self.move_id.doc_type == 'cdp' or \
			(self.move_id.doc_type == 'mod_cdp' and self.mov_type == 'adi_cdp'):
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
			('move_id.fiscal_year', '=', year),('mov_type', 'in', ['cdp','adi_cdp','red_cdp']), ('move_id.name', '!=', self.move_id.name)]
			# if type( self.id ) == int:
			# 	conditions.append( ('id', '!=', self.id) )
			gastos = self.env['presupuesto.moverubros'].search(conditions)
			for gasto in gastos:
				if gasto.mov_type in ('cdp','adi_cdp'):
					utilizado += gasto.ammount
				if gasto.mov_type == 'red_cdp':
					utilizado -= gasto.ammount

		# Utilizado Reducción CDP o Registro presupuestal o Adición registro presupuestal 
		if (self.move_id.doc_type == 'mod_cdp' and self.mov_type == 'red_cdp') or \
			self.move_id.doc_type == 'reg' or \
			(self.move_id.doc_type == 'mod_reg' and self.mov_type == 'adi_reg'):
			# Se obtiene los RP que consumen al CDP
			if self.mov_type != 'adi_reg':
			 	move_rel = self.move_id.move_rel.id
			else:
			 	move_rel = self.move_id.move_rel.move_rel.id
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
			('move_id.fiscal_year', '=', year),('mov_type', '=', 'reg'),
			('move_id.move_rel.id', '=', move_rel),('move_id.name', '!=', self.move_id.name)]
			# if type(self.id) == int:
			# 	conditions.append(('id', '!=', self.id))
			gastos = self.env['presupuesto.moverubros'].search(conditions)
			for gasto in gastos:
				utilizado += gasto.ammount
				conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
				('move_id.fiscal_year', '=', year),('mov_type', 'in', ['adi_reg','red_reg']),
				('move_id.move_rel.id', '=', gasto.move_id.id),('move_id.name', '!=', self.move_id.name)]
				# if type(self.id) == int:
				# 	conditions.append(('id', '!=', self.id))
				modificaciones = self.env['presupuesto.moverubros'].search(conditions)
				for modificacion in modificaciones:
					if modificacion.mov_type == 'adi_reg':
						utilizado += modificacion.ammount
					if modificacion.mov_type == 'red_reg':
						utilizado -= modificacion.ammount
 
 		# Utilizado Reducción Registro presupuestal
		if (self.move_id.doc_type == 'mod_reg' and self.mov_type == 'red_reg'):
			# Se obtiene las Obligaciones que consumen al RP
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
			('move_id.fiscal_year', '=', year),('mov_type', '=', 'obl'),
			('move_id.move_rel.id', '=', self.move_id.move_rel.id)]
			gastos = self.env['presupuesto.moverubros'].search(conditions)
			for gasto in gastos:
				utilizado += gasto.ammount

		# Utilizado Obligación
		if self.move_id.doc_type == 'obl':
			# Se obtiene las obligaciones que consumen el registro presupuestal
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
			('move_id.fiscal_year', '=', year),('mov_type', '=', 'obl'),
			('move_id.move_rel.id', '=', self.move_id.move_rel.id),('move_id.name', '!=', self.move_id.name)]
			# if type(self.id) == int:
			# 	conditions.append(('id', '!=', self.id))
			gastos = self.env['presupuesto.moverubros'].search(conditions)
			for gasto in gastos:
				utilizado += gasto.ammount

		# Utilizado Pago
		if self.move_id.doc_type == 'pago':
			# Se obtiene los pagos que consumen la Obligación
			conditions = [('rubros_id', '=', self.rubros_id.id),('move_id.state', 'in', ['draft','confirm']),
			('move_id.fiscal_year', '=', year),('mov_type', '=', 'pago'),
			('move_id.move_rel.id', '=', self.move_id.move_rel.id), ('move_id.name', '!=', self.move_id.name)]
			# if type(self.id) == int:
			# 	conditions.append(('id', '!=', self.id))
			gastos = self.env['presupuesto.moverubros'].search(conditions)
			for gasto in gastos:
				utilizado += gasto.ammount

		self.saldo_move = formulado - utilizado

		return self.saldo_move	

	@api.onchange('rubros_id')
	def _onchange_rubros_id(self):
		if self.move_id.doc_type not in ('cdp','ini','mod','rec'):
			lista_rubros_cdp = self.env['presupuesto.moverubros'].search([('move_id.id', '=', self.move_id.move_rel.id)]).mapped('rubros_id').ids
			if self.rubros_id.id not in lista_rubros_cdp:
				self.rubros_id = None

		self.saldo_move = self._saldo_move()[ 0 ]
			# return {'value':{},'warning':{'title':'warning','message':'El %s se encuentra en estado borrador, se debe confirmar para continuar' % ( n )}}
		
	@api.constrains('mov_type')   
	def _check_mov_type(self):
		record = self

		if record.move_id.doc_type == 'ini':
			if not (record.mov_type == 'ini'):
				return False
		elif record.move_id.doc_type == 'mod':
			if not (record.mov_type == 'adi' or record.mov_type =='red' or record.mov_type =='cre' or record.mov_type =='cont'):
				return False
		elif record.move_id.doc_type == 'rec':
			if not (record.mov_type == 'rec'):
				return False
		elif record.move_id.doc_type == 'cdp':
			if not (record.mov_type == 'cdp'):
				return False
		elif record.move_id.doc_type == 'reg':
			if not (record.mov_type == 'reg'):
				return False
		elif record.move_id.doc_type == 'obl':
			if not (record.mov_type == 'obl'):
				return False
		elif record.move_id.doc_type == 'pago':
			if not (record.mov_type == 'pago'):
				return False
		elif record.move_id.doc_type == 'mod_cdp':
			if not (record.mov_type == 'adi_cdp' or record.mov_type =='red_cdp'):
				return False
		elif record.move_id.doc_type == 'mod_reg':
			if not (record.mov_type == 'adi_reg' or record.mov_type =='red_reg'):
				return False
		return True

	@api.one
	@api.constrains('ammount')   
	def _check_saldo(self):
		saldo_move = self._saldo_move()[ 0 ]

		# if self.mov_type == 'ini' or self.mov_type == 'rec' or self.mov_type == 'adi' or self.mov_type == 'cre' or self.mov_type == 'adi_cdp' or self.mov_type == 'adi_reg':
		if self.mov_type == 'ini' or self.mov_type == 'rec' or self.mov_type == 'adi' or self.mov_type == 'cre':	
			return True
		elif self.ammount > saldo_move:
			raise ValidationError('El valor del movimiento no puede ser superior al saldo.')
		return True  

	def _get_list_mov_type(self):
		list_mov_type = []
		if self.env.context.get('default_doc_type') == 'mod_cdp':
			list_mov_type = [('adi_cdp','Adición CDP'),('red_cdp','Reducción CDP')]	
 		elif self.env.context.get('default_doc_type') == 'mod_reg':
			list_mov_type = [('adi_reg','Adición RP'),('red_reg','Reducción RP')]
		elif self.env.context.get('default_doc_type') == 'ini':	
			list_mov_type = [('ini','Inicial')]
		elif self.env.context.get('default_doc_type') == 'mod':	
			list_mov_type = [('adi','Adición'),('red','Reducción'),('cre','Crédito'),
			('cont','Contracrédito')]
 		else: 
			list_mov_type = [('ini','Inicial'),('adi','Adición'),('red','Reducción'),('cre','Crédito'),
			('cont','Contracrédito'),('rec','Recaudo'),('cdp','CDP'),('reg','Compromiso'),('obl','Obligación'),
			('pago','Pago'),('adi_cdp','Adición CDP'),('red_cdp','Reducción CDP'),
			('adi_reg','Adición RP'),('red_reg','Reducción RP')]	
		return list_mov_type 

	def create(self, vals):
		if vals.get('ammount') <= 0.0 and vals.get('mov_type') != 'ini':
 			raise ValidationError('El monto del rubro debe ser mayor que cero')

		return super(presupuesto_moverubros, self).create(vals)	

	def write(self, vals):
		if vals.get('ammount') and vals.get('ammount') <= 0.0  and vals.get('mov_type') != 'ini':
 			raise ValidationError('El monto del rubro debe ser mayor que cero')

		return super(presupuesto_moverubros, self).write(vals)	

	@api.onchange('mov_type')
	def _onchange_mov_type(self):
		self._saldo_move()


	move_id = fields.Many2one('presupuesto.move', 'Documento', ondelete='cascade', default = lambda self : self.env.context.get('move_id', False) )
	rubros_id = fields.Many2one('presupuesto.rubros', 'Rubros', required=True,  ondelete='restrict')
	mov_type = fields.Selection('_get_list_mov_type', 'Tipo', select=True, required=True)
	saldo_move = fields.Float(string='Saldo', required=True, store=False, compute = '_saldo_move')
	period_id = fields.Many2one('account.period', string = 'Period')
	date = fields.Date(string='Effective date')

	ammount = fields.Float('Valor', required=True)
	notas = fields.Char('Notas', size=60)

	enero = fields.Float('Enero')
	febrero = fields.Float('Febrero')
	marzo = fields.Float('Marzo')
	abril = fields.Float('Abril')
	mayo = fields.Float('Mayo')
	junio = fields.Float('Junio')
	julio = fields.Float('Julio')
	agosto = fields.Float('Agosto')
	septiembre = fields.Float('Septiembre')
	octubre = fields.Float('Octubre')
	noviembre = fields.Float('Noviembre')
	diciembre = fields.Float('Diciembre')

	move_state = fields.Selection('Estado del documento', related='move_id.state', default = 'draft')

	_sql_constraints = [('rubro_unico', 'unique(move_id,rubros_id)', 'Rubro no debe repetirse')]
	# _sql_constraints = [
	# 	('name_company_uniq', 'unique(name, company_id)', 'The name of the period must be unique per company!'),
	# ]