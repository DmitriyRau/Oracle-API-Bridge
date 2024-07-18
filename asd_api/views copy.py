from datetime import datetime
import oracledb
from django.conf import settings
from django.shortcuts import redirect
from django.views.defaults import page_not_found
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

def custom_page_not_found(request, exception):
	return redirect('/not-found/')

class BaseView(APIView):
	"""Базовый класс для обработки запросов к API."""
	permission_classes = [IsAuthenticated]

	# Создание пула соединений при инициализации класса
	@classmethod
	def initialize_connection_pool(cls):
		"""
		Инициализирует пул соединений для базы данных Oracle.

		Этот метод класса создает пул соединений, используя настройки из словаря `settings.DATABASES`.
		Он использует функцию `oracledb.makedsn` для создания DSN (Data Source Name) на основе хоста, порта и имени сервиса.
		Пул соединений создается с использованием класса `oracledb.SessionPool`, с указанием пользователя, пароля, DSN и дополнительных параметров.
		Пул соединений сохраняется как атрибут класса, чтобы его можно было использовать среди экземпляров класса.

		Параметры:
			cls (тип): Объект класса.

		Возвращает:
			None
		"""
		dsn = oracledb.makedsn(
			settings.DATABASES['asd']['HOST'],
			settings.DATABASES['asd']['PORT'],
			service_name=settings.DATABASES['asd']['NAME']
		)
		cls.pool = oracledb.SessionPool(
			user=settings.DATABASES['asd']['USER'],
			password=settings.DATABASES['asd']['PASSWORD'],
			dsn=dsn,
			min=100,
			max=500,
			increment=20,
			threaded=True,
			timeout=60,
			wait_timeout=2
		)

	def post(self, request):
		"""
		Обработка POST-запросов. Получает SQL-запрос и параметры из тела запроса,
		выполняет запрос к Oracle базе данных и возвращает результат.
		Получает SQL-запрос и параметры из тела запроса.
		Проверяет наличие SQL-запроса, возвращает ошибку при отсутствии.
		Устанавливает соединение с базой данных и выполняет SQL-запрос, возвращая результат или ошибку.
		"""
		if not isinstance(request.data, dict):
			return Response({'error': 'Неверный формат данных'}, status=status.HTTP_400_BAD_REQUEST)

		sql = request.data.get('sql')
		params = request.data.get('params', {})

		if not sql:
			return Response({'error': 'SQL-запрос не предоставлен'}, status=status.HTTP_400_BAD_REQUEST)

		try:
			with self.get_connection() as connection:
				with connection.cursor() as cursor:
					result = self.execute_sql(cursor, sql, params)
					connection.commit()
			return Response({'data': result}, status=status.HTTP_200_OK)
		except oracledb.Error as e:
			logger.error(f"Database error: {e}")
			return Response({'error': 'Ошибка базы данных'}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			logger.error(f"Unexpected error: {e}")
			return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get_connection(self):
		"""Получает соединение из пула соединений Oracle базы данных."""
		return self.pool.acquire()
		
	def execute_sql(self, cursor, sql, params):
		"""
		Выполняет SQL-запрос. Если запрос является процедурой, вызывает процедуру,
		иначе выполняет обычный SQL-запрос.
		"""
		if sql.startswith('CALL'):
			return self.call_procedure(cursor, sql[5:], params)
		else:
			return self.execute_query(cursor, sql, params)
		
	def call_procedure(self, cursor, proc_name, params):
		"""
		Вызывает хранимую процедуру в базе данных с переданными параметрами.
		Подготавливает параметры для процедуры и обрабатывает выходные параметры.
		Возвращает результат выполнения процедуры.
		"""
		proc_params, proc_out_params = self.prepare_proc_params(cursor, params)
		cursor.callproc(proc_name, proc_params)
		cursor.connection.commit()

		result = {'message': 'Вызов процедуры выполнен успешно'}
		if proc_out_params:
			result['output'] = self.get_proc_output(cursor, proc_out_params)

		# Соединение возвращается в пул автоматически по with
		return result
	
	def prepare_proc_params(self, cursor, params):
		"""
		Подготавливает параметры для вызова процедуры.
		Разделяет параметры на входные и выходные.
		Возвращает кортеж из списка параметров и словаря выходных параметров.
		"""
		proc_params = []
		proc_out_params = {}

		for key, value in params.items():
			if isinstance(value, dict) and value.get('dir') == 'OUT':
				out_param = cursor.var(getattr(oracledb, value['type']))
				proc_params.append(out_param)
				proc_out_params[key] = out_param
			else:
				if isinstance(value, str) and value.count('-') == 2 and len(value) == 10:
					try:
						value = datetime.strptime(value, '%Y-%m-%d')
					except ValueError as e:
						raise ValidationError(f"Ошибка конвертации даты для параметра '{key}': {e}")
				elif isinstance(value, str) and value.count('-') == 2 and value.count(':') == 2  and len(value) == 19:
					try:
						value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
					except ValueError as e:
						raise ValidationError(f"Ошибка конвертации даты и времени для параметра '{key}': {e}")
				proc_params.append(value)

		return proc_params, proc_out_params


class QueryView(BaseView):
	"""Класс для обработки POST-запросов, содержащих SQL-запросы для Oracle базы данных."""

	def get_proc_output(self, cursor, proc_out_params):
		"""
		Обрабатывает выходные параметры после выполнения процедуры.
		Возвращает словарь с результатами выходных параметров.
		"""
		output_data = {}
		for key, out_param in proc_out_params.items():
			if out_param.type == oracledb.DB_TYPE_CURSOR:
				cursor_out = out_param.getvalue()
				columns = [col[0] for col in cursor_out.description]
				rows = cursor_out.fetchall()
				output_data[key] = [dict(zip(columns, row)) for row in rows]
			else:
				output_data[key] = out_param.getvalue()
		return output_data

	def execute_query(self, cursor, sql, params):
		"""
		Выполняет обычный SQL-запрос с переданными параметрами.
		Возвращает результат выполнения запроса.
		"""
		cursor.execute(sql, params)
		if cursor.description:
			columns = [col[0] for col in cursor.description]
			rows = cursor.fetchall()
			data = [dict(zip(columns, row)) for row in rows]
			return data
		else:
			cursor.connection.commit()
			return []

class DataTableView(BaseView):
	"""Класс для обработки POST-запросов, возвращающих данные в формате JSON DataTable."""

	def get_column_type(self, column_type):
		"""
		Сопоставляемые типы данных колонок
		"""
		column_type_mapping = {
			'DB_TYPE_VARCHAR': ['string', 'DB_TYPE_VARCHAR'],
			'DB_TYPE_NVARCHAR': ['string', 'DB_TYPE_NVARCHAR'],
			'DB_TYPE_NCHAR': ['string', 'DB_TYPE_NCHAR'],
			'DB_TYPE_CHAR': ['string', 'DB_TYPE_CHAR'],
			'DB_TYPE_NUMBER': ['number', 'DB_TYPE_NUMBER'],
			'DB_TYPE_BINARY_FLOAT': ['number', 'DB_TYPE_BINARY_FLOAT'],
			'DB_TYPE_BINARY_DOUBLE': ['number', 'DB_TYPE_BINARY_DOUBLE'],
			'DB_TYPE_DATE': ['date', 'DB_TYPE_DATE'],
			'DB_TYPE_TIMESTAMP': ['date', 'DB_TYPE_TIMESTAMP'],
			'DB_TYPE_TIMESTAMP_WITH_TIMEZONE': ['date', 'DB_TYPE_TIMESTAMP_WITH_TIMEZONE'],
			'DB_TYPE_TIMESTAMP_LTZ': ['date', 'DB_TYPE_TIMESTAMP_LTZ'],
			'DB_TYPE_TIMESTAMP_TZ': ['date', 'DB_TYPE_TIMESTAMP_TZ'],
			'DB_TYPE_TIMESTAMP_UTC': ['date', 'DB_TYPE_TIMESTAMP_UTC'],
			'DB_TYPE_RAW': ['string', 'DB_TYPE_RAW'],
			'DB_TYPE_LONG': ['string', 'DB_TYPE_LONG'],
			'DB_TYPE_BLOB': ['string', 'DB_TYPE_BLOB'],
			'DB_TYPE_CLOB': ['string', 'DB_TYPE_CLOB'],
			'DB_TYPE_NCLOB': ['string', 'DB_TYPE_NCLOB'],
			'DB_TYPE_BOOLEAN': ['boolean', 'DB_TYPE_BOOLEAN'],
			'DB_TYPE_INT64': ['number', 'DB_TYPE_INT64'],
			'DB_TYPE_INT32': ['number', 'DB_TYPE_INT32'],
			'DB_TYPE_INT16': ['number', 'DB_TYPE_INT16'],
			'DB_TYPE_INT8': ['number', 'DB_TYPE_INT8'],
			'DB_TYPE_FLOAT': ['number', 'DB_TYPE_FLOAT'],
			'DB_TYPE_DOUBLE': ['number', 'DB_TYPE_DOUBLE'],
			'DB_TYPE_DECIMAL': ['number', 'DB_TYPE_DECIMAL'],
			'DB_TYPE_BIGINT': ['number', 'DB_TYPE_BIGINT'],
			'DB_TYPE_SMALLINT': ['number', 'DB_TYPE_SMALLINT'],
			'DB_TYPE_TINYINT': ['number', 'DB_TYPE_TINYINT'],
			'DB_TYPE_XML': ['string', 'DB_TYPE_XML'],
			'DB_TYPE_REF_CURSOR': ['string', 'DB_TYPE_REF_CURSOR'],
			'DB_TYPE_TIMESTAMP_WITH_LOCAL_TIME_ZONE': ['date', 'DB_TYPE_TIMESTAMP_WITH_LOCAL_TIME_ZONE'],
			'DB_TYPE_TIMESTAMP_WITH_UTC_TIME_ZONE': ['date', 'DB_TYPE_TIMESTAMP_WITH_UTC_TIME_ZONE'],
			'DB_TYPE_TIMESTAMP_WITH_TIME_ZONE': ['date', 'DB_TYPE_TIMESTAMP_WITH_TIME_ZONE'],
		}
		return column_type_mapping.get(column_type.name, 'string')

	def get_proc_output(self, cursor, proc_out_params):
		"""
		Обрабатывает выходные параметры после выполнения процедуры.
		Возвращает словарь с результатами выходных параметров.
		"""
		output_data = {}
		for key, out_param in proc_out_params.items():
			if out_param.type == oracledb.DB_TYPE_CURSOR:
				cursor_out = out_param.getvalue()
				columns = {col[0]: self.get_column_type(col[1]) for col in cursor_out.description}
				rows = cursor_out.fetchall()
				output_data[key] = {
					"columns": columns, 
					# "data": [dict(zip(columns, row)) for row in rows]}
					"rows": [list(row) for row in rows]
				}
			else:
				output_data[key] = out_param.getvalue()
		return output_data

	def execute_query(self, cursor, sql, params):
		"""
		Выполняет обычный SQL-запрос с переданными параметрами.
		Возвращает результат выполнения запроса.
		"""
		cursor.execute(sql, params)
		if cursor.description:
			columns = {col[0]: self.get_column_type(col[1]) for col in cursor.description}
			rows = cursor.fetchall()
			data = {
				'columns': columns,
				'rows': [list(row) for row in rows]
			}
			return data
		else:
			cursor.connection.commit()
			return {
				'columns': {},
				'rows': []
			}
		
# Инициализация пула соединений при запуске приложения
BaseView.initialize_connection_pool()