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

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_voucher = fields.Char(string="Comprobante de transacción de pago")
    pago_presupuestal = fields.Boolean(string="Indica si el pago proviene del presupuesto", default=False)
    tipo_pago = fields.Selection(string="Tipo de pago", related='journal_id.type')