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
    user = models.OneToOneField(Users, models.DB_CASCADE, primary_key=True)
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
    plan = models.ForeignKey(Plans, models.DB_CASCADE)
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
    conversation = models.ForeignKey(Conversations, models.DB_CASCADE)
    sender = models.ForeignKey(Users, models.DO_NOTHING)
    body = models.TextField()
    created_at = models.TextField()

    class Meta:
        managed = False
        db_table = 'messages'


class Notifications(models.Model):
    user = models.ForeignKey(Users, models.DB_CASCADE)
    kind = models.TextField()
    title = models.TextField()
    body = models.TextField(blank=True, null=True)
    is_read = models.IntegerField()
    created_at = models.TextField()

    class Meta:
        managed = False
        db_table = 'notifications'
