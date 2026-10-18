"""Маршрутизатор двух баз:

- 'default' — копия сайта из Turso (unmanaged-модели, только чтение);
- 'crm'     — постоянная база CRM: комнаты, жильцы, начисления, платежи,
              а также аккаунты/сессии Django (не стираются синком).
"""

SITE_MODELS = {
    'users', 'userprofiles', 'plans', 'planfeatures', 'requests',
    'caretakerrequests', 'conversations', 'messages', 'notifications',
}


class CrmRouter:
    def db_for_read(self, model, **hints):
        return 'default' if model._meta.model_name in SITE_MODELS else 'crm'

    def db_for_write(self, model, **hints):
        return 'default' if model._meta.model_name in SITE_MODELS else 'crm'

    def allow_relation(self, obj1, obj2, **hints):
        dbs = {'default', 'crm'}
        return obj1._state.db in dbs and obj2._state.db in dbs

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name in SITE_MODELS:
            return False  # таблицы сайта живут в Turso, Django их не создаёт
        return db == 'crm'
