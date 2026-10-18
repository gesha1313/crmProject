"""Реальное время: перед обработкой запроса подтягиваем свежие данные Turso.

Локальная turso.db — кеш. Раз в TURSO_SYNC_TTL секунд (по умолчанию 3) любой
запрос к CRM сначала обновляет кеш из облака, поэтому данные с сайта видны
почти мгновенно, а записи из CRM (write-through) не теряются.
"""
import threading
import time

from . import turso

_last = {'t': 0.0}
_lock = threading.Lock()


def _ttl():
    try:
        return max(1, int(__import__('os').environ.get('TURSO_SYNC_TTL', '3')))
    except ValueError:
        return 3


class TursoRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        skip = path.startswith(('/static/', '/login', '/register', '/admin'))
        if not skip and turso.enabled() and time.time() - _last['t'] > _ttl():
            with _lock:
                if time.time() - _last['t'] > _ttl():
                    _last['t'] = time.time()
                    try:
                        from django.core.management import call_command
                        call_command('pull_turso', verbosity=0)
                        from .sync_residents import sync_residents
                        sync_residents()
                    except Exception as exc:
                        print(f'[sync] обновление из Turso не удалось: {exc}')
        return self.get_response(request)
