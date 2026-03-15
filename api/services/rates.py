from django.db import transaction

from api.models import ExchangeRate, RateAuditLog


@transaction.atomic
def upsert_exchange_rate(*, pair, rate, as_of, source, changed_by=None, note=""):
    existing = ExchangeRate.objects.filter(pair=pair, as_of=as_of).first()

    if existing:
        existing.rate = rate
        existing.source = source
        existing.save(update_fields=["rate", "source"])

        RateAuditLog.objects.create(
            pair=pair,
            rate=rate,
            source=source,
            action=RateAuditLog.Action.UPDATED,
            changed_by=changed_by,
            note=note,
        )
        return existing, False

    new_rate = ExchangeRate.objects.create(
        pair=pair,
        rate=rate,
        as_of=as_of,
        source=source,
    )

    RateAuditLog.objects.create(
        pair=pair,
        rate=rate,
        source=source,
        action=RateAuditLog.Action.CREATED,
        changed_by=changed_by,
        note=note,
    )
    return new_rate, True