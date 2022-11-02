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

import logging

_logger = logging.getLogger(__name__)
import base64

from datetime import datetime

class cargue(models.TransientModel):
	_name = "presupuesto.cargue"
	_description = "Cargue de presupuesto"
				
	move_id = fields.Many2one('presupuesto.move', 'Presupuesto', required = True, ondelete = 'cascade')
	file = fields.Binary('Archivo')

	state = fields.Selection([('sin_procesar', 'Sin procesar'),('procesado', 'Procesado')], 'Estado', default = 'sin_procesar')

	def to_float(self, string):
		string = string.replace('.', '')
		string = string.replace(',', '.')


		try:
			float(string)
			return string
		except ValueError:
			pass
	 
		try:
			import unicodedata
			unicodedata.numeric(string)
			return string
		except (TypeError, ValueError):
			pass
	 
		return False



	@api.multi
	def start(self):

		if self.state == 'procesado':
			raise ValidationError('El archivo fue procesado')

		rubro_model = self.env['presupuesto.rubros']
		presupuesto_rubros_model = self.env['presupuesto.moverubros']

		text = base64.b64decode( self.file )
		text = text.split("\n")

		ant = False
		# Creando rubros
		for line in text:
			if line:
				line_split = line.split(";")
				codigo = line_split[ 0 ].strip()


				inicia = -1
				entra = True
				parent_id = False
				while entra:

					comparar = codigo[ 0 : inicia  ]

					if inicia == len( codigo ) * -1:
						break

					_logger.info("comparar")	
					_logger.info( comparar )

					parent_id = rubro_model.search([('code', '=', comparar  ),('rubro_tipo', '=', 'G' if line_split[ 3 ].strip() == 'GASTOS' else 'I'  )], limit = 1)
					if parent_id:
						parent_id = parent_id.id
						break

					_logger.info("encuentra")
					_logger.info( parent_id )


					inicia -= 1	


				_logger.info("cargando")
				_logger.info( line_split[ 0 ].strip() )
				_logger.info( line_split[ 2 ].strip() )


				res = rubro_model.create({
					'code' : line_split[ 0 ].strip(),
					'rubro_nivel' : 'S' if line_split[ 1 ].strip() == 'MAYOR' else 'D',
					'name' : line_split[ 2 ].strip(),
					'rubro_tipo' : 'G' if line_split[ 3 ].strip() == 'GASTOS' else 'I',
					'parent_id' : parent_id

				})



				if line_split[ 1 ] == 'MAYOR':
					continue		

				presupuesto_rubros_model.create({
					'mov_type' : 'ini',
					'rubros_id' : res.id,
					'ammount' : self.to_float( line_split[ 4 ].strip() )  ,
					'move_id' : self.move_id.id,
					'enero' : self.to_float( line_split[ 5 ].strip() ) ,
					'febrero' : self.to_float( line_split[ 6 ].strip() ) ,
					'marzo' : self.to_float( line_split[ 7 ].strip() ) ,
					'abril' : self.to_float( line_split[ 8 ].strip() ) ,
					'mayo' : self.to_float( line_split[ 9 ].strip() ) ,
					'junio' : self.to_float( line_split[ 10 ].strip() ) ,
					'julio' : self.to_float( line_split[ 11 ].strip() ) ,
					'agosto' : self.to_float( line_split[ 12 ].strip() ) ,
					'septiembre' : self.to_float( line_split[ 13 ].strip() ),
					'octubre' : self.to_float( line_split[ 14 ].strip() ) ,
					'noviembre' : self.to_float( line_split[ 15 ].strip() ) ,
					'diciembre' : self.to_float( line_split[ 16 ].strip() ) 
				})

				ant = line_split[ 0 ]

		# Cargando rubros + valores al presupuesto seleccionado


		self.state = 'procesado'

class PresupuestoCarqueDocumeto(models.TransientModel):
	_name = "presupuesto.cargue.documento"
	_description = "Cargue de documentos de presupuesto"
	doc_type = fields.Selection([('cdp', 'CDP'),
		('mod_cdp', 'Modificaciones CDP'),
		('reg', 'RP'),
		('mod_reg', 'Modificaciones RP'),
		('obl', 'Ordenes de Pago'),
		('pago', 'Pago')], 'Tipo de documento a migrar', default = 'cdp')			
	file = fields.Binary('Archivo')
	procesar = fields.Boolean('', default = False)

	def to_float_documentos(self, string):
		string = string.replace('.', '')
		string = string.replace(',', '.')

		try:
			float(string)
			return string
		except ValueError:
			pass
	 
		try:
			import unicodedata
			unicodedata.numeric(string)
			return string
		except (TypeError, ValueError):
			pass
	 
		return False

	@api.onchange('file','doc_type')
	def _onchange_file(self):
		if self.file:
			self.procesar = True
		
	@api.multi
	def migrate_documents(self):

		move = self.env['presupuesto.move']
		moverubros = self.env['presupuesto.moverubros']

		text = base64.b64decode( self.file )
		text = text.split("\n")

		# Creando documentos		
		lista_rubros = []
		movimiento_detalle = []
		documento_ant = ''		
		fiscalyear = self.env['account.fiscalyear'].search([('state', '=', 'draft')])
		for documento_line in text:
			if documento_line:
				documento_line_split = documento_line.split(";")
				if documento_line_split[ 0 ].strip():
					if documento_line_split[ 0 ].strip() != documento_ant:
						if lista_rubros:
							move_nuevo = move.create({'doc_type' : self.doc_type,
							 'fiscal_year' : fiscalyear.id,
							 'period_id' : periodo.id,
							 'date_start' : fiscalyear.date_start,
							 'date_stop' : fiscalyear.date_stop,
							 'date' : fecha_documento_str,
							 'move_rel' : documento_move_rel,
							 'description' : descripcion,
							 'id_externo' : documento_ant,
							 'partner_id' : tercero,
							 'invoice_id' : factura,
							 'payslip_id' : nomina,
							 'voucher_id' : voucher,
							 'contract_id' : contrato,
							 'gastos_ids' : lista_rubros})
							if estado_documento == 'confirm':
								move_nuevo.button_confirm()
							if estado_documento == 'void':
								move_nuevo.button_void()
							if estado_documento == 'rejected':
								move_nuevo.button_rejected()
							
						lista_rubros = []
						fecha_documento_str = ''	
						if documento_line_split[ 1 ].strip():
							fecha_documento_str = documento_line_split[ 1 ].strip()
							mes = datetime.strptime(fecha_documento_str, '%d/%m/%Y').month
							periodo = self.env['account.period'].search([('id', '=', mes)])
						documento_relacionado = ''						
						if documento_line_split[ 2 ].strip():
							documento_relacionado = documento_line_split[ 2 ].strip()
						estado_documento = ''
						if documento_line_split[ 8 ].strip():
							estado_documento = documento_line_split[ 8 ].strip()
						descripcion = documento_line_split[ 3 ].strip()
						documento_ant = documento_line_split[ 0 ].strip()
						doc_type_ant = self.doc_type

						# Verifica si ya existe el identificador externo
						if doc_type_ant in ('cdp','mod_cdp','reg','mod_reg','obl','pago'):
							identificador_externo = self.env['presupuesto.move'].search([('doc_type', '=', doc_type_ant),('id_externo', '=', documento_ant)])  
							if identificador_externo:
								mensaje_error = 'El documento origen ' + str(documento_ant) + ' ya fue importado anteriormente'
								raise ValidationError(_(mensaje_error))									

						# Documento relacionado modificación CDP y RP
						if doc_type_ant == ('cdp'):
							documento_move_rel = 0

						# Documento relacionado modificación CDP y RP
						if doc_type_ant in ('mod_cdp','reg'):
							documento_move_rel = self.env['presupuesto.move'].search([('doc_type', '=', 'cdp'),('id_externo', '=', documento_relacionado),('state', '=', 'confirm')]).id  
							if documento_move_rel == False:
								mensaje_error = 'El CDP ' + documento_relacionado + ' no existe o no está confirmado'
								raise ValidationError(_(mensaje_error))									
						
						# Documento relacionado RP y modificación RP 
						if doc_type_ant in ('mod_reg','obl'):
							documento_move_rel = self.env['presupuesto.move'].search([('doc_type', '=', 'reg'),('id_externo', '=', documento_relacionado),('state', '=', 'confirm')]).id  
							if documento_move_rel == False:
								mensaje_error = 'El RP ' + documento_relacionado + ' no existe o no está confirmado'
								raise ValidationError(_(mensaje_error))										

						# Documento relacionado pago presupuestal 
						if doc_type_ant == ('pago'):
							documento_move_rel = self.env['presupuesto.move'].search([('doc_type', '=', 'obl'),('id_externo', '=', documento_relacionado),('state', '=', 'confirm')]).id  
							if documento_move_rel == False:
								mensaje_error = 'La Orden de pago ' + documento_relacionado + ' no existe o no está confirmada'
								raise ValidationError(_(mensaje_error))										

						# Tercero
						tercero = 0
						if documento_line_split[ 9 ].strip():
							nombre_tercero = documento_line_split[ 9 ].strip()
							tercero = self.env['res.partner'].search([('name', '=', nombre_tercero)]).id
							if tercero == False:
								raise ValidationError(_('No existe el tercero xxxxx'))

						# Nomina
						nomina = 0
						if documento_line_split[ 10 ].strip():
							descripcion_nomina = documento_line_split[ 10 ].strip()
							nomina = self.env['hr.payslip'].search([('name', '=', descripcion_nomina)]).id
							if nomina == False:
								raise ValidationError(_('No existe el nomina xxxxx'))

						# Factura
						factura = 0
						if documento_line_split[ 11 ].strip():
							numero_factura = documento_line_split[ 11 ].strip()
							factura = self.env['account.invoice'].search([('number', '=', numero_factura)]).id
							if factura == False:
								raise ValidationError(_('No existe el factura xxxxx'))					

						# Comprobante
						voucher = 0
						if documento_line_split[ 12 ].strip():
							numero_voucher = documento_line_split[ 12 ].strip()
							voucher = self.env['account.payment'].search([('name', '=', numero_voucher)]).id
							if voucher == False:
								raise ValidationError(_('No existe el voucher xxxxx'))

						# Contrato
						contrato = 0
						if documento_line_split[ 13 ].strip():
							numero_contrato = documento_line_split[ 13 ].strip()
							contrato = self.env['hr.contract'].search([('name', '=', numero_contrato)]).id
							if contrato == False:
								raise ValidationError(_('No existe el contrato xxxxx'))					

				rubro = self.env['presupuesto.rubros'].search([('code', '=', documento_line_split[ 4 ].strip())])
				if rubro:
					if self.doc_type != 'cdp':
						rubro_move_rel = self.env['presupuesto.moverubros'].search([('rubros_id.id', '=', rubro.id), ('move_id', '=', documento_move_rel)]).id
						if rubro_move_rel == False:
							mensaje_error = 'El rubro ' + rubro.code + ' ' + rubro.name + ' no pertenece al documento relacionado'
							raise ValidationError(_(mensaje_error))	
					if documento_line_split[ 5 ].strip():
						tipo_movimiento = documento_line_split[ 5 ].strip()
					else:
						tipo_movimiento = self.doc_type
				else:
					mensaje_error = 'El rubro ' + documento_line_split[ 4 ].strip() + ' no existe en el maestro de rubros'
					raise ValidationError(_(mensaje_error))

				# Valida que el tipo de documento a migrar coincida con el tipo de documento seleccionado
				if self.doc_type == 'mod_cdp':
					movimiento_detalle = ['adi_cdp','red_cdp']
				elif self.doc_type == 'mod_reg':
					movimiento_detalle = ['adi_reg','red_reg']
				else:
					movimiento_detalle = self.doc_type

				if tipo_movimiento not in movimiento_detalle:
					raise ValidationError(_('El tipo de documento a importar no es del mismo tipo del seleccionado'))

				lista_rubros.append((0,0,{
					'rubros_id' : rubro.id, 
					'mov_type' : tipo_movimiento,
					'ammount' : self.to_float_documentos(documento_line_split[ 6 ].strip()),
					'notas' : documento_line_split[ 7 ].strip(),
					'date' : fields.Date.today(), 
					'period_id' : periodo.id}))

		if lista_rubros:
			move_nuevo = move.create({'doc_type' : self.doc_type,
			 'fiscal_year' : fiscalyear.id,
			 'period_id' : periodo.id,
			 'date_start' : fiscalyear.date_start,
			 'date_stop' : fiscalyear.date_stop,
			 'date' : fecha_documento_str,
			 'move_rel' : documento_move_rel,
			 'description' : descripcion,
			 'state' : estado_documento,
			 'id_externo' : documento_ant,
			 'partner_id' : tercero,
			 'invoice_id' : factura,
			 'payslip_id' : nomina,
			 'voucher_id' : voucher,
			 'contract_id' : contrato,
			 'gastos_ids' : lista_rubros})
			if estado_documento == 'confirm':
				move_nuevo.button_confirm()
			if estado_documento == 'void':
				move_nuevo.button_void()
			if estado_documento == 'rejected':
				move_nuevo.button_rejected()