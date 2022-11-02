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


class presupuesto_move(models.Model):
	_name = 'hr.contract'
	_inherit = 'hr.contract'

	cdp = fields.Many2one('presupuesto.move', 'CDP', ondelete='restrict', states={'confirm': [('readonly', True)]})
	
	
