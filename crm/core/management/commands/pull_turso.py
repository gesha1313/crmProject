"""Синхронизация: Turso → локальный кеш SQLite, которым читает Django.

«Мягкий» рефреш: все таблицы запрашиваются одним batch-запросом к HTTP API v2
и перезаливаются в кеж через DELETE + INSERT OR REPLACE. Файл не пересоздаётся,
поэтому открытые соединения и write-through записи не страдают.
"""
import base64
import json
import os
import sqlite3
import urllib.request
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.core.management.base import BaseCommand, CommandError


def _post(http_base, token, requests_body):
    req = urllib.request.Request(
        http_base.rstrip('/') + '/v2/pipeline',
        data=json.dumps({'requests': requests_body}).encode(),
        headers={'Authorization': 'Bearer ' + token,
                 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    results = []
    for res in data.get('results', []):
        if res.get('type') != 'ok':
            raise CommandError(f'Turso вернул ошибку: {json.dumps(res)[:300]}')
        results.append(res['response']['result'])
    return results


def _value(cell):
    if cell is None:
        return None
    if cell.get('type') == 'blob':
        return base64.b64decode(cell['value'])
    return cell.get('value')


class Command(BaseCommand):
    help = 'Обновляет локальный кеш данными из Turso (мягкий рефреш)'

    def handle(self, *args, **options):
        url = os.environ.get('TURSO_DATABASE_URL', '').strip()
        token = os.environ.get('TURSO_AUTH_TOKEN', '').strip()
        if not (url.startswith('libsql://') or url.startswith('https://')) or not token:
            self.stdout.write('TURSO_DATABASE_URL / TURSO_AUTH_TOKEN не заданы — синк пропущен')
            return
        http_base = 'https://' + url[len('libsql://'):] if url.startswith('libsql://') else url

        schema = _post(http_base, token, [{'type': 'execute', 'stmt': {
            'sql': "SELECT name, sql FROM sqlite_master "
                   "WHERE type='table' AND name NOT LIKE 'sqlite_%'"}}])[0]
        tables = [(row[0]['value'], row[1]['value']) for row in schema['rows']]
        if not tables:
            raise CommandError('В Turso не найдено ни одной таблицы')

        data = _post(http_base, token, [
            {'type': 'execute', 'stmt': {'sql': f'SELECT * FROM "{name}"'}}
            for name, _ in tables
        ])

        path = str(settings.DATABASES['default']['NAME'])
        fresh = not os.path.exists(path)
        if fresh:  # первый запуск — создать файл и схему
            con = sqlite3.connect(path)
            try:
                for _, ddl in tables:
                    con.execute(ddl)
                con.commit()
            finally:
                con.close()

        total = 0
        with connections['default'].cursor() as cur:
            cur.execute('PRAGMA foreign_keys = OFF')  # полная перезаливка кеша
            for (name, ddl), res in zip(tables, data):
                if fresh:
                    cur.execute(ddl.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1))
                cols = [c['name'] for c in res['cols']]
                rows = [tuple(_value(c) for c in row) for row in res['rows']]
                cur.execute(f'DELETE FROM "{name}"')
                if rows:
                    collist = ', '.join(f'"{c}"' for c in cols)
                    cur.executemany(
                        f'INSERT OR REPLACE INTO "{name}" ({collist}) '
                        f'VALUES ({", ".join(["%s"] * len(cols))})', rows)
                total += len(rows)
            cur.execute('PRAGMA foreign_keys = ON')
        Path(path).touch()
        self.stdout.write(self.style.SUCCESS(
            f'Turso → {path}: таблиц {len(tables)}, строк {total}'))
