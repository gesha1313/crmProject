from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.shortcuts import render, redirect
from django.db.models import Count

from .models import (Users, UserProfiles, Requests, CaretakerRequests,
                     Conversations, Messages, Notifications)

ROLE_LABELS = {
    'user': 'Клиенты', 'employee': 'Сотрудники',
    'admin': 'Админы', 'caretaker': 'Сиделки',
}
STATUS_LABELS = {
    'new': 'Новая', 'in_progress': 'В работе', 'done': 'Завершена', 'cancelled': 'Отменена',
    'offered': 'Предложена сиделке', 'accepted': 'Принята', 'declined': 'Отклонена',
}
STATUS_BADGES = {
    'new': 'warn', 'in_progress': 'ok', 'done': 'gray', 'cancelled': 'gray',
    'offered': 'warn', 'accepted': 'ok', 'declined': 'danger',
}


def _req_rows():
    rows = []
    for r in Requests.objects.select_related('user', 'plan').order_by('-created_at'):
        rows.append({
            'ward': r.ward_name or '—',
            'client': r.user.email if r.user_id else '—',
            'plan': f'{r.plan.name} — {r.plan.monthly_price:,} ₽'.replace(',', ' ') if r.plan else '—',
            'status': STATUS_LABELS.get(r.status, r.status),
            'badge': STATUS_BADGES.get(r.status, 'gray'),
            'created': r.created_at,
        })
    return rows


def _cr_rows():
    rows = []
    for r in (CaretakerRequests.objects.select_related('user', 'caretaker_user')
              .order_by('-created_at')):
        name = 'не назначена'
        if r.caretaker_user_id:
            try:
                name = r.caretaker_user.userprofiles.full_name or r.caretaker_user.email
            except Users.userprofiles.RelatedObjectDoesNotExist:
                name = r.caretaker_user.email
        rows.append({
            'ward': r.ward_name or '—',
            'age': r.ward_age if r.ward_age is not None else '—',
            'client': r.user.email if r.user_id else '—',
            'caretaker': name,
            'status': STATUS_LABELS.get(r.status, r.status),
            'badge': STATUS_BADGES.get(r.status, 'gray'),
            'start': r.start_date or '—',
        })
    return rows


@login_required
def dashboard(request):
    reqs = _req_rows()
    crs = _cr_rows()
    roles = [
        (ROLE_LABELS.get(role, role), n)
        for role, n in Users.objects.values_list('role').annotate(n=Count('id')).order_by('-n')
    ]
    notifs = [
        {'title': n.title, 'user': n.user.email if n.user_id else '—',
         'body': n.body or '', 'created': n.created_at}
        for n in Notifications.objects.select_related('user').order_by('-created_at')[:6]
    ]
    return render(request, 'crm/dashboard.html', {
        'users_total': Users.objects.count(),
        'roles': roles,
        'req_count': Requests.objects.count(),
        'cr_count': CaretakerRequests.objects.count(),
        'msg_count': Messages.objects.count(),
        'conv_count': Conversations.objects.count(),
        'reqs': reqs,
        'crs': crs[:5],
        'notifs': notifs,
    })


@login_required
def residents(request):
    return render(request, 'crm/residents.html', {
        'reqs': _req_rows(),
        'crs': _cr_rows(),
    })


@login_required
def chat(request):
    convs = []
    selected = None
    conv_list = list(Conversations.objects.select_related('user').order_by('id'))
    for c in conv_list:
        convs.append({
            'id': c.id,
            'title': f'Диалог #{c.id} — {c.user.email if c.user_id else "—"}',
            'n': Messages.objects.filter(conversation_id=c.id).count(),
        })
    cid = request.GET.get('c')
    if cid and cid.isdigit():
        selected = Conversations.objects.filter(id=int(cid)).first()
    if selected is None and conv_list:
        selected = conv_list[0]
    messages = []
    if selected:
        for m in (Messages.objects.filter(conversation=selected)
                  .select_related('sender').order_by('created_at')):
            messages.append({
                'sender': m.sender.email if m.sender_id else '—',
                'body': m.body,
                'created': m.created_at,
            })
    return render(request, 'crm/chat.html', {
        'convs': convs,
        'selected_id': selected.id if selected else None,
        'selected_title': f'Диалог #{selected.id} — {selected.user.email}' if selected else 'Нет диалогов',
        'messages': messages,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='dashboard')
def users(request):
    profiles = {p.user_id: p for p in UserProfiles.objects.all()}
    rows = []
    for u in Users.objects.order_by('-created_at'):
        p = profiles.get(u.id)
        rows.append({
            'email': u.email,
            'role': ROLE_LABELS.get(u.role, u.role),
            'name': (p.full_name if p else '') or '—',
            'phone': (p.phone if p else '') or '—',
            'created': u.created_at,
        })
    return render(request, 'crm/users.html', {'rows': rows})


from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email')


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        auth_login(request, user)
        return redirect('dashboard')
    return render(request, 'crm/register.html', {'form': form})
