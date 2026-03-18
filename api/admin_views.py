import csv
import io
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

from .models import Currency, CurrencyPair
from .admin_models import ExchangeRate, RateAuditLog


# Permission helper
def _is_admin(user):
    return user.is_staff or user.is_superuser

# Serializers
def _serialize_currency(c):
    return {
        "id":      c.id,
        "code":    c.code,
        "name":    c.name,
        "symbol":  c.symbol,
        "flag":    c.flag,
        "enabled": c.enabled,
    }


def _serialize_rate(r):
    return {
        "id":         r.id,
        "pair":       str(r.pair),
        "pair_id":    r.pair.id,
        "rate":       str(r.rate),
        "source":     r.source,
        "updated_by": r.updated_by.username if r.updated_by else "system",
        "as_of":      r.as_of.isoformat(),
    }


def _serialize_audit(a):
    return {
        "id":         a.id,
        "pair":       str(a.pair),
        "old_rate":   str(a.old_rate) if a.old_rate else None,
        "new_rate":   str(a.new_rate),
        "source":     a.source,
        "action":     a.action,
        "changed_by": a.changed_by.username if a.changed_by else "system",
        "note":       a.note,
        "created_at": a.created_at.isoformat(),
    }


# GET /api/v1/admin/dashboard/

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):
    """
    Admin dashboard summary stats.
    Returns: total currencies, exchange rate counts, stale/unavailable counts.
    """
    if not _is_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    total_currencies  = Currency.objects.count()
    enabled_currencies = Currency.objects.filter(enabled=True).count()
    total_pairs       = CurrencyPair.objects.filter(enabled=True).count()

    # Rates to count latest rate per pair
    total_rates = ExchangeRate.objects.count()

    # Stale requst when no rate update happened in last 24 hours
    since_24h = timezone.now() - timezone.timedelta(hours=24)
    pairs_with_recent = ExchangeRate.objects.filter(
        as_of__gte=since_24h
    ).values("pair").distinct().count()

    stale_rates       = total_pairs - pairs_with_recent
    unavailable_rates = CurrencyPair.objects.filter(enabled=True).exclude(
        id__in=ExchangeRate.objects.values("pair")
    ).count()

    # Last health check time = most recent ExchangeRate update
    last_rate = ExchangeRate.objects.order_by("-as_of").first()
    last_check = last_rate.as_of.isoformat() if last_rate else None

    return Response({
        "total_currencies":   total_currencies,
        "enabled_currencies": enabled_currencies,
        "total_pairs":        total_pairs,
        "total_rates":        total_rates,
        "stale_rates":        max(stale_rates, 0),
        "unavailable_rates":  unavailable_rates,
        "api_status":         "operational",
        "last_check":         last_check,
        "uptime_pct":         "99.8",   # placeholder
    })


# GET /api/v1/admin/currencies/
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_currencies_list(request):
    """
    GET /admin/currencies/ — list ALL currencies (enabled + disabled).
    Admin only.
    """
    if not _is_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    currencies = Currency.objects.all().order_by("code")
    return Response({"currencies": [_serialize_currency(c) for c in currencies]})


# POST /api/v1/admin/currencies/

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_currency_add(request):
    """
    POST /admin/currencies/add/
    Body: { "code": "AED", "name": "UAE Dirham", "symbol": "د.إ", "flag": "🇦🇪" }
    
    Creates the currency AND auto-creates GBP/NEW pairs with a default rate of 1.0
    Admin should then manually update the rate via /admin/rates/manual/
    """
    if not _is_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    code   = request.data.get("code", "").strip().upper()
    name   = request.data.get("name", "").strip()
    symbol = request.data.get("symbol", "").strip()
    flag   = request.data.get("flag", "").strip()

    if not code or not name or not symbol:
        return Response(
            {"error": "code, name, and symbol are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(code) > 3:
        return Response({"error": "code must be 3 characters max"}, status=status.HTTP_400_BAD_REQUEST)

    if Currency.objects.filter(code=code).exists():
        return Response({"error": f"Currency {code} already exists"}, status=status.HTTP_400_BAD_REQUEST)

    # Create the currency
    currency = Currency.objects.create(
        code=code, name=name, symbol=symbol, flag=flag, enabled=True
    )

    # Auto-create pairs with GBP as base (GBP/NEW_CURRENCY)
    pairs_created = []
    try:
        gbp = Currency.objects.get(code="GBP")

        # GBP/NEW pair — e.g. GBP/AED
        pair, created = CurrencyPair.objects.get_or_create(
            base=gbp,
            quote=currency,
            defaults={"rate": Decimal("1.000000"), "change_pct": Decimal("0"), "enabled": True}
        )
        if created:
            pairs_created.append(str(pair))

    except Currency.DoesNotExist:
        pass  # GBP not in DB yet — skip pair creation

    return Response({
        "currency": _serialize_currency(currency),
        "pairs_created": pairs_created,
        "message": f"{code} added. {len(pairs_created)} pair(s) created with default rate 1.0 — update rates manually.",
    }, status=status.HTTP_201_CREATED)


# admin_views.py ke top mein ye import already hona chahiye:
# from decimal import Decimal, InvalidOperation
# agar nahi hai toh add karo


# PATCH /api/v1/admin/currencies/{id}/toggle/

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def admin_currency_toggle(request, id):
    """
    PATCH /admin/currencies/{id}/toggle/
    Enables or disables a currency.
    """
    if not _is_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    try:
        currency = Currency.objects.get(pk=id)
    except Currency.DoesNotExist:
        return Response({"error": "Currency not found"}, status=status.HTTP_404_NOT_FOUND)

    currency.enabled = not currency.enabled
    currency.save()

    return Response({
        "currency": _serialize_currency(currency),
        "message": f"{currency.code} {'enabled' if currency.enabled else 'disabled'} successfully",
    })


# GET /api/v1/admin/rates/
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_rates_list(request):
    """
    GET /admin/rates/ , recent rate updates, latest per pair.
    """
    if not _is_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    # Latest rate per pair (most recent 50)
    rates = ExchangeRate.objects.select_related("pair__base", "pair__quote", "updated_by").order_by("-as_of")[:50]

    return Response({"rates": [_serialize_rate(r) for r in rates]})


# POST /api/v1/admin/rates/manual/

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_rate_manual(request):
    """
    POST /admin/rates/manual/
    Body: { "pair_id": 1, "rate": "1.2850" }
    Manually update exchange rate for a pair + write audit log.
    """
    if not _is_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    pair_id  = request.data.get("pair_id")
    new_rate = request.data.get("rate")

    if not pair_id or not new_rate:
        return Response({"error": "pair_id and rate are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        new_rate_decimal = Decimal(str(new_rate))
        if new_rate_decimal <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        return Response({"error": "rate must be a positive number"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pair = CurrencyPair.objects.select_related("base", "quote").get(pk=pair_id, enabled=True)
    except CurrencyPair.DoesNotExist:
        return Response({"error": "Pair not found"}, status=status.HTTP_404_NOT_FOUND)

    # Get old rate before updating
    old_rate = pair.rate

    # Update CurrencyPair rate (this is what customer sees)
    pair.rate = new_rate_decimal
    pair.save()

    # Record in ExchangeRate history
    rate_record = ExchangeRate.objects.create(
        pair=pair,
        rate=new_rate_decimal,
        source="manual",
        updated_by=request.user,
    )

    # Write audit log
    RateAuditLog.objects.create(
        pair=pair,
        old_rate=old_rate,
        new_rate=new_rate_decimal,
        source="manual",
        action="updated",
        changed_by=request.user,
    )

    return Response({
        "rate": _serialize_rate(rate_record),
        "message": f"{pair} rate updated: {old_rate} → {new_rate_decimal}",
    }, status=status.HTTP_200_OK)


# POST /api/v1/admin/rates/csv/

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def admin_rate_csv(request):
    """
    POST /admin/rates/csv/
    Upload a CSV file with columns: pair_code, rate
    Example CSV:
        pair_code,rate
        GBP/USD,1.2850
        GBP/EUR,1.1700
    """
    if not _is_admin(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "CSV file is required (field: 'file')"}, status=status.HTTP_400_BAD_REQUEST)

    if not file.name.endswith(".csv"):
        return Response({"error": "Only .csv files are accepted"}, status=status.HTTP_400_BAD_REQUEST)

    decoded = file.read().decode("utf-8")
    reader  = csv.DictReader(io.StringIO(decoded))

    results   = []
    errors    = []
    updated   = 0

    for i, row in enumerate(reader, start=2):  # start=2 because row 1 = header
        pair_code = row.get("pair_code", "").strip().upper()
        rate_str  = row.get("rate", "").strip()

        if not pair_code or not rate_str:
            errors.append({"row": i, "error": "Missing pair_code or rate"})
            continue

        try:
            new_rate = Decimal(rate_str)
            if new_rate <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            errors.append({"row": i, "pair": pair_code, "error": f"Invalid rate: {rate_str}"})
            continue

        # Parse pair code e.g. "GBP/USD"
        parts = pair_code.split("/")
        if len(parts) != 2:
            errors.append({"row": i, "pair": pair_code, "error": "pair_code must be in format BASE/QUOTE"})
            continue

        base_code, quote_code = parts

        try:
            pair = CurrencyPair.objects.select_related("base", "quote").get(
                base__code=base_code,
                quote__code=quote_code,
                enabled=True,
            )
        except CurrencyPair.DoesNotExist:
            errors.append({"row": i, "pair": pair_code, "error": "Pair not found or disabled"})
            continue

        old_rate  = pair.rate
        pair.rate = new_rate
        pair.save()

        ExchangeRate.objects.create(
            pair=pair, rate=new_rate, source="csv", updated_by=request.user
        )
        RateAuditLog.objects.create(
            pair=pair,
            old_rate=old_rate,
            new_rate=new_rate,
            source="csv",
            action="csv",
            changed_by=request.user,
        )

        results.append({"pair": pair_code, "old_rate": str(old_rate), "new_rate": str(new_rate)})
        updated += 1

    return Response({
        "updated": updated,
        "errors":  errors,
        "results": results,
        "message": f"{updated} rate(s) updated successfully" + (f", {len(errors)} error(s)" if errors else ""),
    }, status=status.HTTP_200_OK)