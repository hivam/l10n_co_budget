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


class presupuesto_rp_saldo(models.TransientModel):
	_name = "presupuesto.rp.saldo"
	_description = "Registro presupuestal con saldo pendiente"

	fiscalyear_id =  fields.Many2one('account.fiscalyear', u'Año fiscal', select=True, required=True, default = lambda self: self._get_fiscalyear())
	period_from = fields.Many2one('account.period', 'Periodo inicial', required=True)
	period_to =  fields.Many2one('account.period', 'Periodo final', required=True)
	period_ant =  fields.Many2one('account.period', 'Periodo anterior')

			
	def _get_fiscalyear(self):
		context = self.env.context

		now = time.strftime('%Y-%m-%d')
		company_id = self.env.user.company_id.id

		domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
		fiscalyears = self.env['account.fiscalyear'].search(domain)

		return fiscalyears and fiscalyears[0] or False


	@api.multi
	def create_report_rp_saldo(self):
		res = ''
		company_id = self.env.user.company_id.id
		datos = self.env['presupuesto.move'].search([('doc_type', '=', 'reg'), ('fiscal_year', '=', self.fiscalyear_id.id), ('company_id', '=', company_id), ('state', '=', 'confirm')])
		rp_pendientes = datos.filtered(lambda r: r.amount_available > 0 and r.date >= self.period_from.date_start and r.date <= self.period_to.date_stop)
		if rp_pendientes:
			res = self.env['report'].get_action(rp_pendientes, 'l10n_co_budget.report_rp_saldo')
		else:
			raise ValidationError('No existen Registros Presupuestales con saldo pendiente para el periodo seleccionado')

		return res