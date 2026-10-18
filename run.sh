#!/bin/sh
# Старт CRM: синк с Turso → миграции → статика → админ → сервер
set -e
cd crm
python manage.py pull_turso
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@patronage.ru', 'Admin123!')"
exec gunicorn config.wsgi:application --bind 0.0.0.0:"${PORT:-8000}"
