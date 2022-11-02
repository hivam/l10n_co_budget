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


class presupuesto_ejecucion_ing(models.TransientModel):
	_name = "presupuesto.ejecucion.ingresos.report"
	_description = "Ejecucion de Ingresos Report"
				
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
	active_id = fields.Integer('Active')


class presupuesto_ejecucion_ing(models.TransientModel):
	_name = "presupuesto.ejecucion.ingresos.contables.report"
	_description = "Ejecucion de Ingresos Contables Report"
				
	rubro_codigo = fields.Char('Rubro codigo')
	rubro_nombre = fields.Char('Rubro nombre')
	rubro_nivel = fields.Char('Rubro nivel')
	rubro_codigo_cta_contable = fields.Char('Rubro cuenta contable')
	rubro_nombre_cta_contable = fields.Char('Rubro nombre cuenta contable')
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
	active_id = fields.Integer('Active')
