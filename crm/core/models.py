# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Users(models.Model):
    email = models.TextField(unique=True)
    password_hash = models.TextField()
    role = models.TextField()
    created_at = models.TextField()

    class Meta:
        managed = False
        db_table = 'users'


class UserProfiles(models.Model):
    user = models.OneToOneField(Users, models.CASCADE, primary_key=True)
    full_name = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    updated_at = models.TextField()

    class Meta:
        managed = False
        db_table = 'user_profiles'


class Plans(models.Model):
    name = models.TextField(unique=True)
    monthly_price = models.IntegerField()
    note = models.TextField(blank=True, null=True)
    is_popular = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'plans'


class PlanFeatures(models.Model):
    plan = models.ForeignKey(Plans, models.CASCADE)
    feature = models.TextField()
    sort_order = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'plan_features'


class Requests(models.Model):
    user = models.ForeignKey(Users, models.DO_NOTHING)
    employee = models.ForeignKey(Users, models.DO_NOTHING, related_name='requests_employee_set', blank=True, null=True)
    status = models.TextField()
    message = models.TextField(blank=True, null=True)
    ward_name = models.TextField(blank=True, null=True)
    passport = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    plan = models.ForeignKey(Plans, models.DO_NOTHING, blank=True, null=True)
    created_at = models.TextField()
    updated_at = models.TextField()

    class Meta:
        managed = False
        db_table = 'requests'


class CaretakerRequests(models.Model):
    user = models.ForeignKey(Users, models.DO_NOTHING)
    status = models.TextField()
    ward_name = models.TextField()
    ward_age = models.IntegerField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    tasks = models.TextField(blank=True, null=True)
    start_date = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    caretaker_user = models.ForeignKey(Users, models.DO_NOTHING, related_name='caretakerrequests_caretaker_user_set', blank=True, null=True)
    arrival_minutes = models.IntegerField(blank=True, null=True)
    created_at = models.TextField()
    updated_at = models.TextField()
    end_date = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'caretaker_requests'


class Conversations(models.Model):
    user = models.ForeignKey(Users, models.DO_NOTHING)
    employee = models.ForeignKey(Users, models.DO_NOTHING, related_name='conversations_employee_set', blank=True, null=True)
    status = models.TextField()
    created_at = models.TextField()
    updated_at = models.TextField()

    class Meta:
        managed = False
        db_table = 'conversations'


class Messages(models.Model):
    conversation = models.ForeignKey(Conversations, models.CASCADE)
    sender = models.ForeignKey(Users, models.DO_NOTHING)
    body = models.TextField()
    created_at = models.TextField()

    class Meta:
        managed = False
        db_table = 'messages'


class Notifications(models.Model):
    user = models.ForeignKey(Users, models.CASCADE)
    kind = models.TextField()
    title = models.TextField()
    body = models.TextField(blank=True, null=True)
    is_read = models.IntegerField()
    created_at = models.TextField()

    class Meta:
        managed = False
        db_table = 'notifications'


# ============================================================
# CRM-модели (managed): живут в отдельной базе crm.db.
# Связи с данными сайта (users/requests из Turso) — только по id,
# без ForeignKey: базы разные.
# ============================================================

class Room(models.Model):
    number = models.CharField('Номер', max_length=8, unique=True)
    floor = models.PositiveSmallIntegerField('Этаж')
    capacity = models.PositiveSmallIntegerField('Мест', default=1)
    note = models.CharField('Заметка', max_length=200, blank=True)

    class Meta:
        verbose_name = 'комната'
        verbose_name_plural = 'комнаты'
        ordering = ['number']

    def __str__(self):
        return self.number


class Resident(models.Model):
    STATUS_LIVES, STATUS_BOOKED, STATUS_LEFT = 'lives', 'booked', 'left'
    STATUS = [
        (STATUS_LIVES, 'Проживает'),
        (STATUS_BOOKED, 'Бронь'),
        (STATUS_LEFT, 'Выехал'),
    ]

    full_name = models.CharField('ФИО жильца', max_length=200)
    room = models.ForeignKey(Room, verbose_name='комната', null=True, blank=True,
                             on_delete=models.SET_NULL)
    plan_name = models.CharField('тариф', max_length=100, blank=True)
    monthly_price = models.IntegerField('цена, ₽/мес', default=0)
    status = models.CharField('статус', max_length=10, choices=STATUS,
                              default=STATUS_LIVES)
    move_in = models.DateField('заезд', null=True, blank=True)
    move_out = models.DateField('выезд', null=True, blank=True)
    contact = models.CharField('контакт семьи', max_length=200, blank=True)
    site_user_id = models.IntegerField('id на сайте', null=True, blank=True)
    notes = models.TextField('заметки', blank=True)
    created_at = models.DateTimeField('создан', auto_now_add=True)

    class Meta:
        verbose_name = 'жилец'
        verbose_name_plural = 'жильцы'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class Charge(models.Model):
    KIND_LIVE, KIND_EXTRA = 'live', 'extra'
    KINDS = [(KIND_LIVE, 'Проживание'), (KIND_EXTRA, 'Доп. услуга')]

    resident = models.ForeignKey(Resident, verbose_name='жилец',
                                 on_delete=models.CASCADE,
                                 related_name='charges')
    period = models.DateField('период (месяц)')
    amount = models.IntegerField('сумма, ₽')
    kind = models.CharField('тип', max_length=5, choices=KINDS, default=KIND_LIVE)
    title = models.CharField('назначение', max_length=200, blank=True)
    created_at = models.DateTimeField('создано', auto_now_add=True)

    class Meta:
        verbose_name = 'начисление'
        verbose_name_plural = 'начисления'
        ordering = ['-period', '-id']

    def __str__(self):
        return f'{self.resident} — {self.amount} ₽ ({self.period:%m.%Y})'


class Payment(models.Model):
    METHODS = [
        ('card', 'Карта'), ('cash', 'Наличные'),
        ('transfer', 'Перевод'), ('account', 'Счёт/юр. лицо'),
    ]

    resident = models.ForeignKey(Resident, verbose_name='жилец',
                                 on_delete=models.CASCADE,
                                 related_name='payments')
    amount = models.IntegerField('сумма, ₽')
    paid_on = models.DateField('дата оплаты')
    period = models.DateField('за период', null=True, blank=True)
    method = models.CharField('способ', max_length=10, choices=METHODS,
                              default='card')
    note = models.CharField('примечание', max_length=200, blank=True)
    created_at = models.DateTimeField('создан', auto_now_add=True)

    class Meta:
        verbose_name = 'платёж'
        verbose_name_plural = 'платежи'
        ordering = ['-paid_on', '-id']

    def __str__(self):
        return f'{self.resident} — {self.amount} ₽ ({self.paid_on:%d.%m.%Y})'
