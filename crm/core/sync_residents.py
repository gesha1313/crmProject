"""Автопополнение жильцов из заявок «в пансионат».

Каждый синк с Turso: заявки со статусами «новая»/«в работе» (только
пансионатные, не сиделки) без соответствующего жильца превращаются
в запись «Бронь». Ручные правки менеджера не перетираются.
"""
from .models import Plans, Requests, Resident


def sync_residents():
    created = 0
    for r in (Requests.objects.select_related('plan')
              .filter(status__in=['new', 'in_progress'])):
        if not r.user_id:
            continue
        ward = (r.ward_name or '').strip()
        same = Resident.objects.filter(site_user_id=r.user_id, full_name=ward)
        if ward and same.exclude(status=Resident.STATUS_LEFT).exists():
            continue
        if not ward and Resident.objects.filter(
                site_user_id=r.user_id).exclude(status=Resident.STATUS_LEFT).exists():
            continue
        plan = Plans.objects.filter(id=r.plan_id).first() if r.plan_id else None
        Resident.objects.create(
            full_name=ward or f'Подопечный по заявке #{r.id}',
            plan_name=plan.name if plan else '',
            monthly_price=plan.monthly_price if plan else 0,
            status=Resident.STATUS_BOOKED,
            site_user_id=r.user_id,
            notes=f'Автоматически из заявки #{r.id} ({r.created_at})',
        )
        created += 1
    return created
