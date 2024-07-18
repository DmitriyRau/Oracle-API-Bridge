"""
WSGI config for asd30 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
# import oracledb

from django.core.wsgi import get_wsgi_application

# # Путь к каталогу с Oracle Instant Client
# oracle_instant_client_dir = r"C:\oracle\instantclient_21_14"
# # Переменные окружения
# os.environ["ORACLE_HOME"] = oracle_instant_client_dir
# os.environ["PATH"] = oracle_instant_client_dir + ";" + os.environ["PATH"]
# # Инициализация Oracle Instant Client
# oracledb.init_oracle_client(lib_dir=oracle_instant_client_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asd30.settings')

application = get_wsgi_application()
