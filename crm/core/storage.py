"""Синхронизация crm.db с файловым хранилищем RelaxDev.

Контейнер платформы стирается при каждом деплое, поэтому постоянная
CRM-база хранится в облаке: при старте скачивается, после каждой записи
изменений — выгружается обратно (консистентный снапшот через sqlite backup).

API: https://relaxdev.ru/api/v1/storage (ключ в env STORAGE_API_KEY).
Upload не перезаписывает файлы — старые версии удаляем перед выгрузкой.
"""
import json
import os
import sqlite3
import tempfile
import urllib.parse
import urllib.request
import uuid

from django.conf import settings

API = 'https://relaxdev.ru/api/v1/storage'
SUBPATH = 'crm'
DB_NAME = 'crm.db'


def enabled():
    return bool(os.environ.get('STORAGE_API_KEY'))


def _key():
    return os.environ.get('STORAGE_API_KEY', '')


def _req(method, url, data=None, auth=True, headers=None, timeout=90):
    h = {}
    if auth:
        h['Authorization'] = 'Bearer ' + _key()
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _is_db_file(path):
    # upload добавляет к имени префикс времени: «<ts>-crm.db»
    return path.rsplit('/', 1)[-1].endswith(DB_NAME)


def _list_db_files():
    qs = urllib.parse.urlencode({'path': SUBPATH})
    data = json.loads(_req('GET', f'{API}/files?{qs}'))
    files = [f for f in data.get('files', [])
             if _is_db_file(f.get('path', ''))]
    files.sort(key=lambda f: f.get('lastModified', ''))
    return files


def db_path():
    return str(settings.DATABASES['crm']['NAME'])


def download_db():
    """Скачивает crm.db из хранилища, если он там есть. True — скачан."""
    if not enabled():
        return False
    files = _list_db_files()
    if not files:
        return False
    f = files[-1]
    content = _req('GET', f.get('fallbackUrl') or f['url'], auth=False)
    tmp = db_path() + '.download'
    with open(tmp, 'wb') as fh:
        fh.write(content)
    os.replace(tmp, db_path())
    return True


def _multipart(fields, filename, content):
    b = '----crmform' + uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(
            f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
            .encode())
    parts.append(
        f'--{b}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{filename}"\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'.encode()
        + content + b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    return b''.join(parts), b


def upload_db():
    """Выгружает консистентный снапшот crm.db в хранилище (заменяя старый)."""
    if not enabled() or not os.path.exists(db_path()):
        return False
    # Снапшот через backup API — не ловим файл посреди транзакции
    tmp = tempfile.mktemp(suffix='.db')
    src = sqlite3.connect(db_path())
    dst = sqlite3.connect(tmp)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    with open(tmp, 'rb') as fh:
        content = fh.read()
    os.unlink(tmp)

    for f in _list_db_files():  # старые версии — удалить, upload не перезаписывает
        _req('DELETE', f"{API}/files?" + urllib.parse.urlencode({'path': f['path']}))

    body, boundary = _multipart({'path': SUBPATH}, DB_NAME, content)
    _req('POST', f'{API}/upload', data=body,
         headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    return True
