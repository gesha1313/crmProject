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
            'id': r.id,
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
            'id': r.id,
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
        'fin': _finance(),
    })


@login_required
def residents(request):
    crm_residents = [{
        'id': r.id, 'name': r.full_name,
        'room': r.room.number if r.room_id else '—',
        'plan': f'{r.plan_name} — {r.monthly_price:,} ₽'.replace(',', ' ')
                if r.plan_name else '—',
        'status': r.get_status_display(),
        'badge': {'lives': 'ok', 'booked': 'warn', 'left': 'gray'}[r.status],
        'move_in': r.move_in, 'move_out': r.move_out or '',
        'contact': r.contact or '—',
    } for r in Resident.objects.select_related('room')]
    return render(request, 'crm/residents.html', {
        'reqs': _req_rows(),
        'crs': _cr_rows(),
        'crm_residents': crm_residents,
    })


@login_required
def resident_checkin(request, pk):
    res = get_object_or_404(Resident, pk=pk)
    form = CheckInForm(request.POST or None,
                       initial={'move_in': timezone.localdate()})
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        res.room = d['room']
        res.move_in = d['move_in']
        res.contact = d['contact']
        res.status = Resident.STATUS_LIVES
        res.save()
        return redirect('residents')
    return render(request, 'crm/edit.html', {
        'edit_title': f'Заселение — {res.full_name} '
                      f'({res.plan_name or "без тарифа"})',
        'form': form})


@login_required
def resident_edit(request, pk):
    res = get_object_or_404(Resident, pk=pk)
    form = ResidentEditForm(request.POST or None, initial={
        'status': res.status, 'room': res.room_id,
        'move_in': res.move_in, 'move_out': res.move_out,
        'plan_name': res.plan_name, 'monthly_price': res.monthly_price,
        'contact': res.contact, 'notes': res.notes})
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        res.status = d['status']
        res.room = d['room']
        res.move_in = d['move_in']
        res.move_out = d['move_out']
        res.plan_name = d['plan_name']
        res.monthly_price = d['monthly_price'] or 0
        res.contact = d['contact']
        res.notes = d['notes']
        res.save()
        return redirect('residents')
    return render(request, 'crm/edit.html', {
        'edit_title': f'Жилец — {res.full_name}',
        'form': form})


@login_required
def chat(request):
    if request.method == 'POST':
        mform = MessageForm(request.POST)
        cid = request.POST.get('c')
        if mform.is_valid() and cid and cid.isdigit() and turso.enabled():
            try:
                sender = turso.employee_id()
                if sender:
                    turso.create('messages', {
                        'conversation_id': int(cid), 'sender_id': sender,
                        'body': mform.cleaned_data['body']})
                    turso.update('conversations', int(cid), {'updated_at': _now()})
            except Exception as exc:
                print(f'[chat] не записано в Turso: {exc}')
        return redirect(f'/chat/?c={cid or ""}')
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
            'id': u.id,
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


# ============================================================
# Этапы 1–2: деньги и справочники CRM (база crm.db)
# ============================================================

from datetime import date as _date

from django.db.models import Sum, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .forms import (ChargeEditForm, CheckInForm, PaymentForm,
                   ResidentEditForm, RoomForm)
from .models import Charge, Payment, Resident, Room

MONTHS_RU = {1: 'Янв', 2: 'Фев', 3: 'Мар', 4: 'Апр', 5: 'Май', 6: 'Июн',
             7: 'Июл', 8: 'Авг', 9: 'Сен', 10: 'Окт', 11: 'Ноя', 12: 'Дек'}


def _add_months(d, k):
    y = d.year + (d.month - 1 + k) // 12
    m = (d.month - 1 + k) % 12 + 1
    return _date(y, m, 1)


def _finance():
    """Данные о деньгах для дашборда."""
    today = timezone.localdate()
    m0 = today.replace(day=1)
    months = [_add_months(m0, -i) for i in range(5, -1, -1)]

    pay_by_m = {
        r['m'].strftime('%Y-%m'): r['s']
        for r in (Payment.objects.filter(paid_on__gte=months[0])
                  .annotate(m=TruncMonth('paid_on')).values('m')
                  .annotate(s=Sum('amount')))
    }
    bars = []
    for m in months:
        val = pay_by_m.get(m.strftime('%Y-%m'), 0)
        bars.append({
            'label': f"{MONTHS_RU[m.month]} {str(m.year)[2:]}",
            'value': val,
            'width': round(val / max(pay_by_m.values()) * 100) if pay_by_m else 0,
        })

    income_m0 = pay_by_m.get(m0.strftime('%Y-%m'), 0)
    payments_cnt_m0 = Payment.objects.filter(paid_on__gte=m0).count()
    avg_check = (charges_m0.filter(kind='live')
                 .aggregate(a=Avg('amount'))['a'] or 0)

    debt_rows = []
    for r in Resident.objects.filter(status=Resident.STATUS_LIVES):
        charged = (Charge.objects.filter(resident=r)
                   .aggregate(s=Sum('amount'))['s'] or 0)
        paid = (Payment.objects.filter(resident=r)
                .aggregate(s=Sum('amount'))['s'] or 0)
        debt = charged - paid
        if debt > 0:
            debt_rows.append({'name': r.full_name, 'room': r.room.number
                              if r.room_id else '—', 'debt': debt})
    debt_rows.sort(key=lambda x: -x['debt'])

    capacity = Room.objects.aggregate(s=Sum('capacity'))['s'] or 0
    living = Resident.objects.filter(status=Resident.STATUS_LIVES).count()
    return {
        'bars': bars,
        'income_m0': income_m0,
        'payments_cnt_m0': payments_cnt_m0,
        'avg_check': int(avg_check),
        'debt_total': sum(d['debt'] for d in debt_rows),
        'debt_rows': debt_rows[:5],
        'living': living,
        'capacity': capacity,
    }


@login_required
def rooms(request):
    form = RoomForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('rooms')
    rooms_list = [{
        'number': rm.number, 'floor': rm.floor, 'capacity': rm.capacity,
        'note': rm.note,
        'living': rm.resident_set.filter(status=Resident.STATUS_LIVES).count(),
    } for rm in Room.objects.all()]
    return render(request, 'crm/rooms.html',
                  {'form': form, 'rooms': rooms_list})


@login_required
def payments(request):
    form = PaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        p = form.save()
        # реестр начислений пополняется сам: платёж = начисленная сумма
        Charge.objects.create(
            resident=p.resident, amount=p.amount,
            period=p.period or p.paid_on.replace(day=1),
            kind=Charge.KIND_LIVE,
            title=f'Платёж ({p.get_method_display()}, {p.paid_on:%d.%m.%Y})'
                  + (f' — {p.note}' if p.note else ''))
        return redirect('payments')
    rows = [{
        'resident': p.resident.full_name if p.resident_id else '—',
        'amount': p.amount, 'paid_on': p.paid_on, 'period': p.period,
        'method': p.get_method_display(), 'note': p.note,
    } for p in (Payment.objects.select_related('resident')
                .order_by('-paid_on', '-id')[:50])]
    total = Payment.objects.aggregate(s=Sum('amount'))['s'] or 0
    return render(request, 'crm/payments.html',
                  {'form': form, 'rows': rows, 'total': total})


@login_required
def charges(request):
    rows = [{
        'id': c.id,
        'resident': c.resident.full_name if c.resident_id else '—',
        'room': c.resident.room.number if c.resident_id and c.resident.room else '—',
        'period': c.period, 'amount': c.amount,
        'kind': c.get_kind_display(), 'title': c.title,
    } for c in (Charge.objects.select_related('resident', 'resident__room')
                .order_by('-id')[:100])]
    total = Charge.objects.aggregate(s=Sum('amount'))['s'] or 0
    return render(request, 'crm/charges.html',
                  {'rows': rows, 'total': total})


@login_required
def charge_edit(request, pk):
    charge = get_object_or_404(Charge, pk=pk)
    form = ChargeEditForm(request.POST or None, instance=charge)
    if request.method == 'POST' and request.POST.get('delete'):
        charge.delete()
        return redirect('charges')
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('charges')
    return render(request, 'crm/edit.html', {
        'edit_title': f'Начисление #{pk} — {charge.resident if charge.resident_id else "—"}',
        'form': form, 'allow_delete': True})


# ============================================================
# Редактирование данных сайта — запись напрямую в Turso
# ============================================================

from django.shortcuts import get_object_or_404

from . import turso
from .forms import (CaretakerEditForm, MessageForm, RequestEditForm,
                    SiteUserEditForm)
from .models import CaretakerRequests as CR
from .models import Requests as Req
from .models import Users as SiteUsers
from .models import UserProfiles as SiteProfiles


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def _request_rows_with_ids():
    """Список заявок с id — для ссылок на редактирование."""
    return [{
        'id': r.id, 'ward': r.ward_name or '—',
        'client': r.user.email if r.user_id else '—',
        'plan': r.plan.name if r.plan_id else '—',
        'status': STATUS_LABELS.get(r.status, r.status),
        'badge': STATUS_BADGES.get(r.status, 'gray'),
        'created': r.created_at,
    } for r in Req.objects.select_related('user', 'plan').order_by('-created_at')]


@login_required
def request_edit(request, pk):
    obj = get_object_or_404(Req, pk=pk)
    form = RequestEditForm(request.POST or None, initial={
        'ward_name': obj.ward_name or '', 'status': obj.status,
        'employee': obj.employee_id or '', 'plan': obj.plan_id or '',
        'message': obj.message or ''})
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        try:
            turso.update('requests', pk, {
                'ward_name': d['ward_name'], 'status': d['status'],
                'employee_id': d['employee'] or None,
                'plan_id': d['plan'] or None,
                'message': d['message'], 'updated_at': _now()})
            if d['status'] != obj.status and obj.user_id:
                turso.create('notifications', {
                    'user_id': obj.user_id, 'kind': 'info',
                    'title': 'Статус заявки обновлён',
                    'body': f'Новый статус: {STATUS_LABELS.get(d["status"], d["status"])}'})
        except Exception as exc:
            return render(request, 'crm/edit.html', {
                'edit_title': f'Заявка #{pk} — {obj.user.email if obj.user_id else "—"}',
                'form': form, 'turso_error': str(exc)})
        return redirect('residents')
    return render(request, 'crm/edit.html', {
        'edit_title': f'Заявка #{pk} — {obj.user.email if obj.user_id else "—"}',
        'form': form})


@login_required
def caretaker_edit(request, pk):
    obj = get_object_or_404(CR, pk=pk)
    form = CaretakerEditForm(request.POST or None, initial={
        'status': obj.status, 'caretaker': obj.caretaker_user_id or '',
        'start_date': obj.start_date or '', 'notes': obj.notes or ''})
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        try:
            turso.update('caretaker_requests', pk, {
                'status': d['status'],
                'caretaker_user_id': d['caretaker'] or None,
                'start_date': d['start_date'], 'notes': d['notes'],
                'updated_at': _now()})
            if d['status'] != obj.status and obj.user_id:
                turso.create('notifications', {
                    'user_id': obj.user_id, 'kind': 'info',
                    'title': 'Заявка на сиделку обновлена',
                    'body': f'Новый статус: {STATUS_LABELS.get(d["status"], d["status"])}'})
        except Exception as exc:
            return render(request, 'crm/edit.html', {
                'edit_title': f'Заявка на сиделку #{pk} — {obj.ward_name}',
                'form': form, 'turso_error': str(exc)})
        return redirect('residents')
    return render(request, 'crm/edit.html', {
        'edit_title': f'Заявка на сиделку #{pk} — {obj.ward_name}',
        'form': form})


@login_required
def site_user_edit(request, pk):
    obj = get_object_or_404(SiteUsers, pk=pk)
    profile = SiteProfiles.objects.filter(user_id=pk).first()
    form = SiteUserEditForm(request.POST or None, initial={
        'role': obj.role,
        'full_name': profile.full_name if profile else '',
        'phone': profile.phone if profile else ''})
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        try:
            turso.update('users', pk, {'role': d['role']})
            if profile:
                turso.update('user_profiles', pk, {
                    'full_name': d['full_name'] or None,
                    'phone': d['phone'] or None, 'updated_at': _now()},
                    pk_col='user')
            else:
                turso.create('user_profiles', {
                    'user': pk, 'full_name': d['full_name'] or None,
                    'phone': d['phone'] or None})
        except Exception as exc:
            return render(request, 'crm/edit.html', {
                'edit_title': f'Пользователь — {obj.email}', 'form': form,
                'turso_error': str(exc)})
        return redirect('users')
    return render(request, 'crm/edit.html', {
        'edit_title': f'Пользователь — {obj.email}', 'form': form})
