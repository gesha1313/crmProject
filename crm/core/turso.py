"""Запись напрямую в Turso (как сайт) + мгновенное обновление локальной копии.

Схема write-through: SQL выполняется в Turso через HTTP API v2 (pipeline),
затем тот же SQL применяется к локальной копии turso.db. Для INSERT новый id
берётся из RETURNING в Turso — локальная копия вставляет строку с тем же id,
поэтому идентификаторы с сайтом не расходятся.
"""
import json
import os
import urllib.request

from django.db import connections


def _http_base():
    url = os.environ.get('TURSO_DATABASE_URL', '')
    if not url:
        return None
    return 'https://' + url[len('libsql://'):] if url.startswith('libsql://') else url


def enabled():
    return bool(_http_base() and os.environ.get('TURSO_AUTH_TOKEN'))


def _arg(value):
    if value is None:
        return {'type': 'null'}
    if isinstance(value, bool):
        return {'type': 'integer', 'value': '1' if value else '0'}
    if isinstance(value, int):
        return {'type': 'integer', 'value': str(value)}
    if isinstance(value, float):
        return {'type': 'float', 'value': str(value)}
    return {'type': 'text', 'value': str(value)}


def execute(sql, args=()):
    """Выполнить SQL в Turso и в локальной копии. Вернуть строки из Turso."""
    base = _http_base()
    if not base:
        raise RuntimeError('Turso не настроен (TURSO_DATABASE_URL/TOKEN)')
    req = urllib.request.Request(
        base.rstrip('/') + '/v2/pipeline',
        data=json.dumps({'requests': [{
            'type': 'execute',
            'stmt': {'sql': sql, 'args': [_arg(a) for a in args]},
        }]}).encode(),
        headers={'Authorization': 'Bearer ' + os.environ['TURSO_AUTH_TOKEN'],
                 'Content-Type': 'application/json'},
        method='POST')
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    res = data['results'][0]
    if res['type'] != 'ok':
        raise RuntimeError(f'Turso отклонил запрос: {json.dumps(res)[:300]}')
    result = res['response']['result']
    cols = [c['name'] for c in result.get('cols', [])]
    rows = [[(c['value'] if c else None) for c in row]
            for row in result.get('rows', [])]
    # тот же SQL — в локальную копию (Django-курсор ждёт %s вместо ?)
    with connections['default'].cursor() as cur:
        cur.execute(sql.replace('?', '%s'), args)
    return [dict(zip(cols, r)) for r in rows]


def create(table, fields):
    """INSERT в Turso (с RETURNING id) и копию. fields — dict колонка→значение."""
    cols = list(fields)
    sql = (f'INSERT INTO "{table}" ({", ".join(cols)}) '
           f'VALUES ({", ".join("?" * len(cols))}) RETURNING id')
    rows = execute(sql, [fields[c] for c in cols])
    new_id = rows[0]['id'] if rows else None
    # локально — с явным id из Turso
    # INSERT OR REPLACE: нумерация копии может расходиться с Turso
    sql_local = (f'INSERT OR REPLACE INTO "{table}" (id, {", ".join(cols)}) '
                 f'VALUES ({", ".join("?" * (len(cols) + 1))})')
    with connections['default'].cursor() as cur:
        cur.execute(sql_local.replace('?', '%s'),
                    [new_id] + [fields[c] for c in cols])
    return int(new_id)


def update(table, row_id, fields, pk_col='id'):
    sets = ', '.join(f'"{c}" = ?' for c in fields)
    execute(f'UPDATE "{table}" SET {sets} WHERE "{pk_col}" = ?',
            list(fields.values()) + [row_id])


def delete(table, row_id):
    execute(f'DELETE FROM "{table}" WHERE id = ?', [row_id])


def employee_id():
    """id сотрудника на сайте — от чьего имени CRM пишет в чаты/уведомления."""
    rows = execute(
        "SELECT id FROM users WHERE role = 'employee' ORDER BY id LIMIT 1")
    return int(rows[0]['id']) if rows else None
