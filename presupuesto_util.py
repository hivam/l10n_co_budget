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
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

import logging

_logger = logging.getLogger(__name__)


class presupuesto_util(models.TransientModel):
	_name = 'presupuesto.util'
	_description = 'Reusable Methods'


	def sql(self, params, context = None):
		browse_model = self.sudo().env[context.get('active_model')].browse(context.get('active_id'))

		fiscalyear = int(browse_model.fiscalyear_id.name)

		date_start = browse_model.period_from.date_start
		date_start_month = date_start.split('-')[ 1 ]

		date_stop = browse_model.period_to.date_stop
		date_stop_month = date_stop.split('-')[ 1 ]

		#mes_anterior = 1 if (int(date_start_month) - 1) == 0 else (int(date_start_month) - 1)
		#fiscalyear_anterior = 1900 if mes_anterior == 0 else fiscalyear
		fiscalyear_anterior = fiscalyear
		mes_anterior = (int(date_start_month) - 1)
		if mes_anterior == 0:
			mes_anterior = 1
			fiscalyear_anterior = 1900


		mes_anterior = "%s-%s-%s" % (fiscalyear, mes_anterior , calendar.monthrange( fiscalyear, mes_anterior )[ 1 ] )
		primer_periodo = '%s-%s-%s' % ( str(fiscalyear), '01', '01' )

		# Fechas para reporte de Gastos.
		date_stop_fecha = '%s-%s-%s' % ( str(fiscalyear), str( date_stop_month ), '01' )

		date_stop_fecha_anterior = False
		date_stop_fecha_anterior_ultimo_dia = False

		if (int(date_stop_month) - 1) > 0:
			date_stop_fecha_anterior = '%s-%s-%s' % ( str(fiscalyear), str( int(date_stop_month) - 1 ), '01' )			
			date_stop_fecha_anterior_ultimo_dia = "%s-%s-%s" % (fiscalyear, str( int(date_stop_month) - 1 ) , calendar.monthrange( fiscalyear, int(date_stop_month) - 1  )[ 1 ] )
		else:
			date_stop_fecha_anterior = '1900-01-01'
			date_stop_fecha_anterior_ultimo_dia = '1900-01-01'
				


		data = {
			'fiscalyear' : str(fiscalyear),
			'primer_periodo' : primer_periodo,
			'date_stop' : date_stop,
			'mes_anterior_fecha' : mes_anterior,            

			'mes_anterior' : '01',
			
			'date_start' : date_start,
			'date_start_month' : date_start_month,
			
			'date_stop_month' : date_stop_month,
			
			'fiscalyear_anterior' : fiscalyear_anterior,
			'rubro_tipo' : params.get('rubro_tipo'),

			'date_stop_fecha' : date_stop_fecha,
			'date_stop_fecha_anterior' : date_stop_fecha_anterior,
			'date_stop_fecha_anterior_ultimo_dia' : date_stop_fecha_anterior_ultimo_dia

		}

		_logger.info( data )


		sql = '''
		SET datestyle TO 'iso, dmy';

		create temp table temp_account_move_line (id int, account_id int, invoice_id int, debit numeric(12,2), credit numeric(12,2));
		create temp table temp_account_saldo (account_id int, debito_mes numeric(12,2), credito_mes numeric(12,2), debito_acu numeric(12,2), credito_acu numeric(12,2));  

		/* Se obtine las distintas cuentas contables que afectan a una factura */
		insert into temp_account_move_line
        select distinct aml.id,aml.account_id,aml.invoice_id,aml.debit,aml.credit
	      from presupuesto_moverubros pmr JOIN presupuesto_move pm
		    ON pm.id = pmr.move_id
		                                  JOIN presupuesto_rubros pr
		    ON pr.id = pmr.rubros_id                                  
		                          	  JOIN account_move_line aml 
		    ON aml.account_id = pr.account_id
		   and aml.invoice_id = pm.invoice_id
		 where pmr.mov_type    = 'obl'  
		   and pm.state        = 'confirm'
		   and pm.date between '%(primer_periodo)s' and '%(date_stop)s';		   

		/* Se obtine el total de débitos y créditos del mes y acumulado según un rango de fecha */
		insert into temp_account_saldo
		select aml.account_id,sum(case when pm.date between '%(date_stop_fecha)s' and '%(date_stop)s' then aml.debit else 0 end),
		                      sum(case when pm.date between '%(date_stop_fecha)s' and '%(date_stop)s' then aml.credit else 0 end),
		                      sum(aml.debit),
		                      sum(aml.credit)
		  from presupuesto_moverubros pmr JOIN presupuesto_move pm
		    ON pm.id = pmr.move_id
		                                  JOIN presupuesto_rubros pr
		    ON pr.id = pmr.rubros_id                                  
		                          	  	  JOIN temp_account_move_line aml 
		    ON aml.account_id = pr.account_id
		 where pmr.mov_type    = 'obl'  
		   and pm.state        = 'confirm'
		   and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		   and pm.invoice_id   = aml.invoice_id
		 group by aml.account_id;


		select pr.id,pr.parent_left,pr.parent_right,pr.code rubro_codigo,pr.name rubro_nombre, pr.rubro_nivel, 
			   coalesce(ac.code,' ') as rubro_codigo_cta_contable, coalesce(ac.name,' ') as rubro_nombre_cta_contable,
			   coalesce(acs.debito_mes,0) as obligacion_cta_mes_actual,
			   coalesce(acs.debito_acu,0) as obligacion_cta_acumulado,
		
		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end as rubro_amount,

		
		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end as adiciones ,

		
		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end as reducciones,

		
		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end as  creditos,

		
		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end as contracreditos,

		
		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end + 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end - 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end  + 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end - 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end as apropiacion_definitiva,

		
		case when
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(mes_anterior_fecha)s' and date_part('year',pm.date) = %(fiscalyear_anterior)s 
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(mes_anterior_fecha)s' and date_part('year',pm.date) = %(fiscalyear_anterior)s 
		) end as ejecutado_anterior,

		
		case when
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(date_start)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(date_start)s' and '%(date_stop)s'
		)  end as ejecutado_periodo,

		
		case when
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(mes_anterior_fecha)s' and date_part('year',pm.date) = %(fiscalyear_anterior)s 
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(mes_anterior_fecha)s' and date_part('year',pm.date) = %(fiscalyear_anterior)s 
		) end + case when

		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(date_start)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(date_start)s' and '%(date_stop)s'
		)  end as total_ejecutado,


		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end + 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end - 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end  + 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end - 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end -
		

		(case when
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(mes_anterior_fecha)s' and date_part('year',pm.date) = %(fiscalyear_anterior)s
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(mes_anterior_fecha)s' and date_part('year',pm.date) = %(fiscalyear_anterior)s
		) end + case when

		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(date_start)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(date_start)s' and '%(date_stop)s'
		)  end) as saldo_por_ejecutar,
		
		
		case
		when ( case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end + 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end - 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end  + 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end - 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end ) = 0 then 0
		else


		((case when
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(mes_anterior_fecha)s' and date_part('year',pm.date) = %(fiscalyear_anterior)s
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(mes_anterior_fecha)s' and date_part('year',pm.date) = %(fiscalyear_anterior)s
		) end + case when

		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(date_start)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'rec'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(date_start)s' and '%(date_stop)s'
		)  end) /
		( case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end + 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end - 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end  + 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end - 

		case when 
		(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
		pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
		and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
		and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
		) end )) * 100 

		end  as porcentaje ''' % ( data )

		if params.get('rubro_tipo') == 'G':
			sql += '''
				, (case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) end 
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) end) as cdp_mes_anterior,

				(case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) end 
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) end) as cdp_mes_actual,

				(case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end  
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end) as cdp_acumulado,

				(case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'ini'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end 
				+
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'adi'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end 
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end  
				+
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end  
				+
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'cre'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end 
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'cont'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end 
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end  ) as apropiacion_disponible,


				(case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) end
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) end) as registro_mes_anterior,


				(case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) end
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) end) as registro_mes_actual,

				(case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end  
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end) as registro_acumulado,

				(case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end 				
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end
				+
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end ) as comprometer,
				
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'obl'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'obl'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) end as obligacion_mes_anterior,

				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'obl'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'obl'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) end as obligacion_mes_actual,

				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'obl'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'obl'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end as obligacion_acumulado,

				( case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('cdp','adi_cdp') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end 
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_cdp' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end  
				-  
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type in ('reg','adi_reg') and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end
				+
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'red_reg' and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end

				) as por_obligar,
				
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'pago'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'pago'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha_anterior)s' and '%(date_stop_fecha_anterior_ultimo_dia)s'
				) end as pago_mes_anterior,

				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'pago'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'pago'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(date_stop_fecha)s' and '%(date_stop)s'
				) end as pago_mes_actual,

				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'pago'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'pago'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end as pago_acumulado,


				( case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'obl'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'obl'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end
				-
				case when 
				(select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'pago'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) is null then 0 else (select sum(ammount)  from presupuesto_moverubros pmr, presupuesto_move pm where 
				pmr.rubros_id in ( select id from presupuesto_rubros pr2 where pr2.parent_left >= pr.parent_left and pr2.parent_right <= pr.parent_right ) 
				and mov_type = 'pago'  and pm.id = pmr.move_id and pm.state = 'confirm'
				and pm.date between '%(primer_periodo)s' and '%(date_stop)s'
				) end ) as por_pagar

			''' % ( data )

		#sql += ''' from presupuesto_rubros pr 
		sql += ''' from presupuesto_rubros pr left join account_account ac on ac.id = pr.account_id
		                                      left join temp_account_saldo acs on acs.account_id = pr.account_id
		where rubro_tipo = '%(rubro_tipo)s' and pr.id in( ( 
		select pr3.id from presupuesto_rubros pr3,presupuesto_move pm3,presupuesto_moverubros pmr3 where
		pm3.id = pmr3.move_id and pmr3.rubros_id = pr3.id and pm3.date between '01-01-%(fiscalyear)s' and '31-12-%(fiscalyear)s' and  pm3.state = 'confirm'
		)) or (rubro_nivel = 'S' and rubro_tipo = '%(rubro_tipo)s'  )
		order by parent_left asc

		''' % ( data )

		self.sudo().env.cr.execute( sql ) 

		
		# pm3.id = pmr3.move_id and pmr3.rubros_id = pr3.id and pm3.date between '01-01-%(fiscalyear)s' and '31-12-%(fiscalyear)s' and  pm3.state = 'confirm'

		datos = []
		for row in self.sudo().env.cr.dictfetchall():

			info = {
				'rubro_codigo' : row.get('rubro_codigo'),
				'rubro_nombre' : row.get('rubro_nombre'),
				'rubro_nivel' : row.get('rubro_nivel'),
				'rubro_codigo_cta_contable' : row.get('rubro_codigo_cta_contable'),
				'rubro_nombre_cta_contable' : row.get('rubro_nombre_cta_contable'),
				'rubro_amount' : row.get('rubro_amount'),
				'adiciones' : row.get('adiciones'),
				'reducciones' : row.get('reducciones'),
				'creditos' : row.get('creditos'),
				'contracreditos' : row.get('contracreditos'),
				'apropiacion_definitiva' : row.get('apropiacion_definitiva'),
				'ejecutado_anterior' : row.get('ejecutado_anterior'),
				'ejecutado_mes' : row.get('ejecutado_periodo'),
				'total_ejecutado' : row.get('total_ejecutado'),
				'saldo_por_ejecutar' : row.get('saldo_por_ejecutar'),
				'porcentaje' : row.get('porcentaje'),
				
			}

			if params.get('rubro_tipo') == 'G':
				info.update({
					'cdp_mes_anterior' : row.get('cdp_mes_anterior'),
					'cdp_mes_actual' : row.get('cdp_mes_actual'),
					'cdp_acumulado' : row.get('cdp_acumulado'),
					'apropiacion_disponible' : row.get('apropiacion_disponible'),

					'registro_mes_anterior' : row.get('registro_mes_anterior'),
					'registro_mes_actual' : row.get('registro_mes_actual'),
					'registro_acumulado' : row.get('registro_acumulado'),
					'comprometer' : row.get('comprometer'),

					'obligacion_mes_anterior' : row.get('obligacion_mes_anterior'),
					'obligacion_mes_actual' : row.get('obligacion_mes_actual'),
					'obligacion_acumulado' : row.get('obligacion_acumulado'),
					'por_obligar' : row.get('por_obligar'),

					'obligacion_cta_mes_actual' : row.get('obligacion_cta_mes_actual'),
					'obligacion_cta_acumulado' : row.get('obligacion_cta_acumulado'),

					'pago_mes_anterior' : row.get('pago_mes_anterior'),
					'pago_mes_actual' : row.get('pago_mes_actual'),
					'pago_acumulado' : row.get('pago_acumulado'),
					'por_pagar' : row.get('por_pagar'),
				})

			datos.append( info )


		return [datos, fiscalyear, date_start, date_stop]

	