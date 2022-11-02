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



class presupuesto_conceptos(models.Model):
	_name = 'presupuesto.conceptos'
	_description = 'Conceptos de presupuesto'
	_rec_name = 'concepto'

	concepto  =  fields.Char('Concepto',size=30)
	rubros_id =  fields.Many2one('presupuesto.rubros', 'Rubro',size=10)


class account_voucher(models.Model):
	_inherit = 'account.voucher'
	_description = 'Voucher'

	rec = fields.Many2one('presupuesto.move', 'Recaudo Presupuestal', domain=[('doc_type', '=' , 'rec'), ('state','=','confirm')], readonly=True, states={'draft':[('readonly',False)]})
	rubro_pres = fields.Many2one('presupuesto.conceptos', 'Concepto Presupuestal',readonly=True, states={'draft':[('readonly',False)]})
	rec_aut = fields.Boolean('Presupuesto Automático',readonly=True, states={'draft':[('readonly',False)]}, default = 1)
	obl = fields.Many2one('presupuesto.move', 'OBL', domain=[('doc_type', '=' , 'obl'), ('state','=','confirm')])
	pago = fields.Many2one('presupuesto.move', 'PAGO', domain=[('doc_type', '=' , 'pago'), ('state','=','confirm')],readonly=True, states={'draft':[('readonly',False)]})