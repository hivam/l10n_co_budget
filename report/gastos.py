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


class presupuesto_ejecucion_gas(models.TransientModel):
	_name = "presupuesto.ejecucion.gastos.report"
	_description = "Ejecucion de Gastos Report"
				
	rubro_codigo = fields.Char('Rubro codigo')
	rubro_nombre = fields.Char('Rubro nombre')
	rubro_nivel = fields.Char('Rubro nivel')
	rubro_amount = fields.Float('Rubro amount')
	adiciones = fields.Float('Adiciones')
	reducciones = fields.Float('Reducciones')
	creditos = fields.Float('Creditos')
	contracreditos = fields.Float('Contracreditos')
	apropiacion_definitiva = fields.Float('Apropiacion definitiva')
	ejecutado_anterior = fields.Float('Ejecutado anterior')
	ejecutado_mes = fields.Float('Ejecutado periodo')
	total_ejecutado = fields.Float('Total ejecutado')
	saldo_por_ejecutar  = fields.Float('Saldo por ejecutar')
	porcentaje = fields.Float('Porcentaje')
	cdp_mes_anterior = fields.Float('cdp_mes_anterior')
	cdp_mes_actual = fields.Float('cdp_mes_actual')
	cdp_acumulado = fields.Float('cdp_acumulado')
	apropiacion_disponible = fields.Float('apropiacion_disponible')
	registro_mes_anterior = fields.Float('registro_mes_anterior')
	registro_mes_actual = fields.Float('registro_mes_actual')
	registro_acumulado = fields.Float('registro_acumulado')
	comprometer = fields.Float('comprometer')
	obligacion_mes_anterior = fields.Float('obligacion_mes_anterior')
	obligacion_mes_actual = fields.Float('obligacion_mes_actual')
	obligacion_acumulado = fields.Float('obligacion_acumulado')
	por_obligar = fields.Float('por_obligar')
	pago_mes_anterior = fields.Float('pago_mes_anterior')
	pago_mes_actual = fields.Float('pago_mes_actual')
	pago_acumulado = fields.Float('pago_acumulado')
	por_pagar = fields.Float('por_pagar')
	active_id = fields.Integer('Active')


class presupuesto_ejecucion_gastos_contables_report(models.TransientModel):
	_name = "presupuesto.ejecucion.gastos.contables.report"
	_description = "Ejecucion de Gastos Report"
				
	rubro_codigo = fields.Char('Rubro codigo')
	rubro_nombre = fields.Char('Rubro nombre')
	rubro_nivel = fields.Char('Rubro nivel')
	rubro_codigo_cta_contable = fields.Char('Rubro cuenta contable')
	rubro_nombre_cta_contable = fields.Char('Rubro nombre cuenta contable')
	obligacion_mes_actual = fields.Float('obligacion_mes_actual')
	obligacion_acumulado = fields.Float('obligacion_acumulado')
	obligacion_cta_mes_actual = fields.Float('obligacion_mes_actual')
	obligacion_cta_acumulado = fields.Float('obligacion_acumulado')
	pago_mes_actual = fields.Float('pago_mes_actual')
	pago_acumulado = fields.Float('pago_acumulado')
	active_id = fields.Integer('Active')