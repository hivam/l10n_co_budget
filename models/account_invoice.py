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



class account_invoice(models.Model):
	_inherit = 'account.invoice'
	_description = 'Account'

	rp = fields.Many2one('presupuesto.move', 'RP', ondelete='restrict', domain=[('doc_type', '=' , 'reg'), ('state','=','confirm')])
	obl = fields.Many2one('presupuesto.move', 'OBL', domain=[('doc_type', '=' , 'obl'), ('state','=','confirm')])
