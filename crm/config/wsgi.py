"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Подготовка базы при старте (любой сервер: runserver, gunicorn, ...).
# Пропускается только родительский процесс автоперезагрузки runserver.
_argv = ' '.join(sys.argv)
_is_reloader_parent = ('runserver' in _argv and '--noreload' not in _argv
                       and not os.environ.get('RUN_MAIN'))
if not _is_reloader_parent:
    try:
        from core.bootstrap import run
        run()
    except Exception as exc:
        print(f'[bootstrap] ошибка: {exc}', file=sys.stderr)
