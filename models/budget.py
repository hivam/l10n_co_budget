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

class co_presupuesto(models.Model):
	_name = 'presupuesto'
	_order = 'idcodigo'
	

	idcodigo = fields.Char('Code', requerid=True)
	name = fields.Char('Name')
		

	@api.multi
	def name_get(self):

		if not self.id:
			return []

		reads = self.read(['name','idcodigo'])
		res = []
		for record in reads:
			name = record['name']
			if record['idcodigo']:
				name = record['idcodigo'] + ' - ' + name
			res.append((record['id'], name))
		return res

	@api.model
	def name_search(self, name, args=None, operator='ilike', context=None, limit=100):
		args = args or []
		ids = []
		if name:
			ids = self.search([('idcodigo', 'ilike', name)] + args, limit=limit, context=context)
			if not ids:
				ids = self.search([('name', operator, name)] + args, limit=limit, context=context)
		else:
			ids = self.search(args, limit=limit, context=context)
		return self.name_get()