#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
# import oracledb

# # Путь к каталогу с Oracle Instant Client
# oracle_instant_client_dir = r"C:\\oracle\\instantclient_21_14"
# # Переменные окружения
# os.environ["ORACLE_HOME"] = oracle_instant_client_dir
# os.environ["PATH"] = oracle_instant_client_dir + ";" + os.environ["PATH"]
# # Инициализация Oracle Instant Client
# oracledb.init_oracle_client(lib_dir=oracle_instant_client_dir)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asd30.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
