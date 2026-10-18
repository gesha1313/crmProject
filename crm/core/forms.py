from django import forms

from .models import Charge, Payment, Resident, Room


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['number', 'floor', 'capacity', 'note']


class ResidentForm(forms.ModelForm):
    class Meta:
        model = Resident
        fields = ['full_name', 'room', 'plan_name', 'monthly_price', 'status',
                  'move_in', 'move_out', 'contact', 'site_user_id', 'notes']
        widgets = {'move_in': forms.DateInput(attrs={'type': 'date'}),
                   'move_out': forms.DateInput(attrs={'type': 'date'}),
                   'notes': forms.Textarea(attrs={'rows': 2})}


class ChargeForm(forms.ModelForm):
    class Meta:
        model = Charge
        fields = ['resident', 'period', 'amount', 'kind', 'title']
        widgets = {'period': forms.DateInput(attrs={'type': 'date'})}

    def clean_period(self):
        d = self.cleaned_data['period']
        return d.replace(day=1)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['resident', 'amount', 'paid_on', 'period', 'method', 'note']
        widgets = {'paid_on': forms.DateInput(attrs={'type': 'date'}),
                   'period': forms.DateInput(attrs={'type': 'date'})}


# ===== Формы редактирования данных сайта (запись напрямую в Turso) =====

class RequestEditForm(forms.Form):
    ward_name = forms.CharField(label='Подопечный', max_length=200, required=False)
    status = forms.ChoiceField(label='Статус', choices=[])
    employee = forms.ChoiceField(label='Менеджер', choices=[], required=False)
    plan = forms.ChoiceField(label='Тариф', choices=[], required=False)
    message = forms.CharField(label='Комментарий', required=False,
                              widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Plans, Users
        from .models import UserProfiles
        self.fields['status'].choices = [
            ('new', 'Новая'), ('in_progress', 'В работе'),
            ('done', 'Завершена'), ('cancelled', 'Отменена')]
        self.fields['employee'].choices = [('', '— не назначен —')] + [
            (u.id, u.email) for u in Users.objects.filter(
                role__in=['employee', 'admin']).order_by('id')]
        self.fields['plan'].choices = [('', '— без тарифа —')] + [
            (p.id, f'{p.name} — {p.monthly_price:,} ₽'.replace(',', ' '))
            for p in Plans.objects.all()]


class CaretakerEditForm(forms.Form):
    status = forms.ChoiceField(label='Статус', choices=[])
    caretaker = forms.ChoiceField(label='Сиделка', choices=[], required=False)
    start_date = forms.CharField(label='Дата начала', max_length=20, required=False)
    notes = forms.CharField(label='Пожелания', required=False,
                            widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Users
        self.fields['status'].choices = [
            ('new', 'Новая'), ('offered', 'Предложена сиделке'),
            ('accepted', 'Принята'), ('declined', 'Отклонена'),
            ('cancelled', 'Отменена')]
        names = {p.user_id: (p.full_name or '') for p in
                 UserProfiles.objects.all()}
        self.fields['caretaker'].choices = [('', '— не назначена —')] + [
            (u.id, names.get(u.id) or u.email) for u in
            Users.objects.filter(role='caretaker').order_by('id')]


class SiteUserEditForm(forms.Form):
    role = forms.ChoiceField(label='Роль', choices=[
        ('user', 'Клиент'), ('employee', 'Сотрудник'),
        ('caretaker', 'Сиделка'), ('admin', 'Админ')])
    full_name = forms.CharField(label='Имя', max_length=200, required=False)
    phone = forms.CharField(label='Телефон', max_length=30, required=False)


class MessageForm(forms.Form):
    body = forms.CharField(label='Сообщение', max_length=2000,
                           widget=forms.TextInput(attrs={
                               'placeholder': 'Написать от имени сотрудника…'}))
