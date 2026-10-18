"""Синхронизация: Turso → локальный SQLite, которым пользуется Django.

Работает через HTTP API v2 (pipeline) без внешних зависимостей:
схема берётся из sqlite_master, данные — обычными SELECT * по таблицам.
"""
import base64
import json
import os
import sqlite3
import urllib.request
from pathlib import Path

from django.conf import settings
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
    help = 'Тянет схему и данные из Turso в локальный файл SQLite'

    def handle(self, *args, **options):
        url = os.environ.get('TURSO_DATABASE_URL', '')
        token = os.environ.get('TURSO_AUTH_TOKEN', '')
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
        Path(path).unlink(missing_ok=True)
        con = sqlite3.connect(path)
        try:
            for (name, ddl), res in zip(tables, data):
                cols = [c['name'] for c in res['cols']]
                con.execute(ddl)
                rows = [tuple(_value(c) for c in row) for row in res['rows']]
                if rows:
                    marks = ','.join('?' * len(cols))
                    collist = ','.join(f'"{c}"' for c in cols)
                    con.executemany(
                        f'INSERT INTO "{name}" ({collist}) VALUES ({marks})', rows)
            con.commit()
        finally:
            con.close()
        total = sum(r for r in (len(x['rows']) for x in data))
        self.stdout.write(self.style.SUCCESS(
            f'Turso → {path}: таблиц {len(tables)}, строк {total}'))
