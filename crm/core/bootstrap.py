"""Автозагрузка при старте приложения: синк с Turso, миграции CRM-базы, админ.

Платформа запускает приложение по-своему (свой run-скрипт, без нашего run.sh),
поэтому подготовка базы выполняется прямо при импорте WSGI-приложения.
"""
import os
import sys

from django.conf import settings
from django.core.management import call_command

from . import storage


def run():
    from django.contrib.auth.models import User

    try:
        call_command('pull_turso', verbosity=0)
    except Exception as exc:  # сеть/Turso могут быть недоступны — не мешаем старту
        print(f'[bootstrap] pull_turso пропущен: {exc}', file=sys.stderr)

    crm_db = str(settings.DATABASES['crm']['NAME'])
    if not os.path.exists(crm_db):
        try:
            if storage.download_db():
                print(f'[bootstrap] crm.db скачан из хранилища', file=sys.stderr)
        except Exception as exc:
            print(f'[bootstrap] скачать crm.db не удалось: {exc}', file=sys.stderr)

    call_command('migrate', database='crm', interactive=False, verbosity=0)

    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@patronage.ru', 'Admin123!')
        print('[bootstrap] создан админ admin', file=sys.stderr)

    try:
        if storage.upload_db():  # выгрузить состояние после миграций
            print('[bootstrap] crm.db выгружен в хранилище', file=sys.stderr)
    except Exception as exc:
        print(f'[bootstrap] выгрузка crm.db не удалась: {exc}', file=sys.stderr)
