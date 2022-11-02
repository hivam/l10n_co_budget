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



class presupuesto_rubros(models.Model):
	_name = 'presupuesto.rubros'

	_order = 'parent_left'
	_parent_order = 'code'
	_parent_store = True




	@api.multi
	def name_get(self):


		reads = self.read(['name','code'])
		res = []
		for record in reads:
			name = record['name']
			if record['code']:
				name = record['code'] + ' - ' + name or ''
			res.append((record['id'], name))
		return res

	@api.model
	def name_search(self, name, args=None, operator='ilike', context=None, limit=100):
		args = args or []
		ids = []
		if name:
			ids = self.search([('code', 'ilike', name)] + args, limit=limit)
			if not ids:
				ids = self.search([('name', operator, name)] + args, limit=limit)
		else:
			ids = self.search(args, limit=limit)



		if ids:
			return ids.name_get()
		return self.name_get()


	"""def _get_children_and_consol(self, ids = False):
		ids = ids or [ self.id ]
		#this function search for all the children and all consolidated children (recursively) of the given account ids
		ids2 = self.search([('parent_id', 'child_of', ids)])
		ids3 = []
		for rec in self.browse(ids2):
			for child in rec.child_consol_ids:
				ids3.append(child.id)
		if ids3:
			ids3 = self._get_children_and_consol(ids3)
		return ids2 + ids3

		
	def _get_level(self,field_name, arg, context=None):
		res = {}
		for rubro in self.browse(ids):
			#we may not know the level of the parent at the time of computation, so we
			# can't simply do res[account.id] = account.parent_id.level + 1
			level = 0
			parent = rubro.parent_id
			while parent:
				level += 1
				parent = parent.parent_id
			res[rubro.id] = level
		return res"""
		

	code = fields.Char(u'Rubro', requerid=True)
	name = fields.Char(u'Nombre')
	rubro_nivel = fields.Selection([('S', 'Mayor'), ('D', 'Detalle')], 'Nivel')
	rubro_tipo = fields.Selection([('I', 'Ingresos'), ('G', 'Gastos')], 'Tipo')
	parent_id = fields.Many2one('presupuesto.rubros', 'Rubro mayor', ondelete='cascade')
	child_ids = fields.One2many('presupuesto.rubros', 'parent_id', 'Child Categories')
	active = fields.Boolean('Activo', default = 1)

	parent_left =  fields.Integer('Left parent', select=True)
	parent_right =  fields.Integer('Right parent', select=True)
	company_id =  fields.Many2one('res.company', 'Company', required=True, default = lambda self: self.env.user.company_id.id )
	sum =  fields.Float(string="Year Sum")
	sum_period =  fields.Float(string="Suma para movimientos")
	sum_ejec =  fields.Float(string="Suma para ejecución")
	child_consol_ids = fields.Many2many('presupuesto.rubros', 'presupuesto_rubros_consol_rel', 'child_id', 'parent_id', 'Consolidated Children')
	level =  fields.Integer(string='Level')
	
	account_id = fields.Many2one('account.account', 'Cuenta contable')