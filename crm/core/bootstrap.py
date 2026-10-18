"""Автозагрузка при старте приложения: синк с Turso, миграции CRM-базы, админ.

Платформа запускает приложение по-своему (свой run-скрипт, без нашего run.sh),
поже подготовка базы выполняется прямо при импорте WSGI-приложения.
"""
import sys

from django.core.management import call_command


def run():
    from django.contrib.auth.models import User

    try:
        call_command('pull_turso', verbosity=0)
    except Exception as exc:  # сеть/Turso могут быть недоступны — не мешаем старту
        print(f'[bootstrap] pull_turso пропущен: {exc}', file=sys.stderr)

    call_command('migrate', database='crm', interactive=False, verbosity=0)

    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@patronage.ru', 'Admin123!')
        print('[bootstrap] создан админ admin', file=sys.stderr)
