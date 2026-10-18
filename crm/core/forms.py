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
