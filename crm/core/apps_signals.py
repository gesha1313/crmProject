"""После каждой записи в CRM-модели — выгрузить базу в хранилище."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import storage
from .models import Charge, Payment, Resident, Room


def _sync(**_):
    try:
        storage.upload_db()
    except Exception as exc:  # хранилище недоступно — не ломаем работу CRM
        print(f'[storage] выгрузка не удалась: {exc}')


def connect():
    for model in (Room, Resident, Charge, Payment):
        post_save.connect(_sync, sender=model)
        post_delete.connect(_sync, sender=model)
