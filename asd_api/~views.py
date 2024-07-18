from datetime import datetime
from django.shortcuts import render
import oracledb
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

class OracleBaseView(APIView):
	"""Базовый класс для работы с Oracle базой данных."""

	def get_connection(self):
		"""Создает и возвращает соединение с Oracle базой данных, используя настройки из settings.DATABASES."""
		dsn = oracledb.makedsn(
			settings.DATABASES['default']['HOST'],
			settings.DATABASES['default']['PORT'],
			service_name=settings.DATABASES['default']['NAME']
		)
		return oracledb.connect(
			user=settings.DATABASES['default']['USER'],
			password=settings.DATABASES['default']['PASSWORD'],
			dsn=dsn
		)

	def execute_sql(self, cursor, sql, params):
		"""Выполняет SQL-запрос с переданными параметрами и возвращает результат."""
		cursor.execute(sql, params)
		if cursor.description:
			columns = [col[0] for col in cursor.description]
			rows = cursor.fetchall()
			return {
				'columns': columns,
				'rows': [dict(zip(columns, row)) for row in rows]
			}
		else:
			cursor.connection.commit()
			return {
				'columns': [],
				'rows': []
			}

class OracleQueryView(OracleBaseView):
	"""Класс для обработки POST-запросов, содержащих SQL-запросы для Oracle базы данных."""
	
	def post(self, request):
		"""
		Обработка POST-запросов. Получает SQL-запрос и параметры из тела запроса,
		выполняет запрос к Oracle базе данных и возвращает результат.
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
			return Response({'data': result}, status=status.HTTP_200_OK)
		except oracledb.Error as e:
			logger.error(f"Database error: {e}")
			return Response({'error': 'Ошибка базы данных'}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			logger.error(f"Unexpected error: {e}")
			return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class OracleDataTableView(OracleBaseView):
	"""Класс для получения данных из Oracle базы данных в табличном формате."""
	
	def post(self, request):
		"""
		Обработка POST-запросов. Получает имя таблицы и параметры из тела запроса,
		выполняет запрос к Oracle базе данных и возвращает данные таблицы.
		"""
		if not isinstance(request.data, dict):
			return Response({'error': 'Неверный формат данных'}, status=status.HTTP_400_BAD_REQUEST)

		table_name = request.data.get('table_name')
		params = request.data.get('params', {})

		if not table_name:
			return Response({'error': 'Имя таблицы не предоставлено'}, status=status.HTTP_400_BAD_REQUEST)

		sql = f"SELECT * FROM {table_name}"
		
		try:
			with self.get_connection() as connection:
				with connection.cursor() as cursor:
					result = self.execute_sql(cursor, sql, params)
			return Response({'data': result}, status=status.HTTP_200_OK)
		except oracledb.Error as e:
			logger.error(f"Database error: {e}")
			return Response({'error': 'Ошибка базы данных'}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			logger.error(f"Unexpected error: {e}")
			return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)