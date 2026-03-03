from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Currency, CurrencyPair, PortfolioHolding
from decimal import Decimal



# AUTH API

@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    username = request.data.get("username")
    password = request.data.get("password")
    email = request.data.get("email", "")
    role = request.data.get("role", "customer")  # "customer" | "admin"

    if not username or not password:
        return Response({"error": "username and password required"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"error": "username already exists"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password, email=email)

    if role == "admin":
        user.is_staff = True
        user.save()

    return Response({"ok": True}, status=status.HTTP_201_CREATED)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    role = "admin" if (u.is_staff or u.is_superuser) else "customer"
    return Response({
        "user": {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": role,
        }
    })

@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    # JWT logout is handled client-side (delete tokens).
    return Response({"ok": True})

# @api_view(["GET"])
# def currencies_list(request):
#     currencies = [
#   { "code": 'GBP', "name": 'British Pound', "symbol": '£', "flag": '🇬🇧', "enabled": True },
#   { "code": 'USD', "name": 'US Dollar', "symbol": '$', "flag": '🇺🇸', "enabled": True },
#   { "code": 'EUR', "name": 'Euro', "symbol": '€', "flag": '🇪🇺', "enabled": True },
#   { "code": 'JPY', "name": 'Japanese Yen', "symbol": '¥', "flag": '🇯🇵', "enabled": True },
#   { "code": 'CNY', "name": 'Chinese Yuan', "symbol": '¥', "flag": '🇨🇳', "enabled": True },
#   { "code": 'HKD', "name": 'Hong Kong Dollar', "symbol": 'HK$', "flag": '🇭🇰', "enabled": True },
#   { "code": 'AUD', "name": 'Australian Dollar', "symbol": 'A$', "flag": '🇦🇺', "enabled": True },
#   { "code": 'CAD', "name": 'Canadian Dollar', "symbol": 'C$', "flag": '🇨🇦', "enabled": True },
#   { "code": 'CHF', "name": 'Swiss Franc', "symbol": 'CHF', "flag": '🇨🇭', "enabled": True },
#   { "code": 'SGD', "name": 'Singapore Dollar', "symbol": 'S$', "flag": '🇸🇬', "enabled": True },
# ]
#     return Response({"currencies": currencies})


# CURRENCIES API  –  GET /currencies?search=

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def currencies_list(request):
    search = request.query_params.get("search", "").strip().upper()
    qs = Currency.objects.filter(enabled=True)
    if search:
        qs = qs.filter(code__icontains=search) | qs.filter(name__icontains=search)

    currencies = [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "symbol": c.symbol,
            "flag": c.flag,
            "enabled": c.enabled,
        }
        for c in qs
    ]
    return Response({"currencies": currencies})


# PAIRS API –  GET /pairs?search=

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pairs_list(request):
    search = request.query_params.get("search", "").strip().upper()
    qs = CurrencyPair.objects.filter(enabled=True).select_related("base", "quote")

    if search:
        qs = qs.filter(base__code__icontains=search) | qs.filter(quote__code__icontains=search) | \
             qs.filter(base__name__icontains=search) | qs.filter(quote__name__icontains=search)

    pairs = [
        {
            "id": p.id,
            "base": {"code": p.base.code, "name": p.base.name, "symbol": p.base.symbol, "flag": p.base.flag},
            "quote": {"code": p.quote.code, "name": p.quote.name, "symbol": p.quote.symbol, "flag": p.quote.flag},
            "pair": f"{p.base.code}/{p.quote.code}",
            "rate": str(p.rate),
            "change_pct": str(p.change_pct),
        }
        for p in qs
    ]
    return Response({"pairs": pairs})


# PORTFOLIO API –  GET /portfolio

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio(request):
    holdings = PortfolioHolding.objects.filter(user=request.user).select_related("currency")

    holding_list = []
    total_value_gbp = Decimal("0")

    for h in holdings:
        # Try to get GBP rate for this currency to calc value
        gbp_value = None
        try:
            gbp_currency = Currency.objects.get(code="GBP")
            if h.currency.code == "GBP":
                gbp_value = h.amount
            else:
                pair = CurrencyPair.objects.get(base=gbp_currency, quote=h.currency)
                gbp_value = h.amount / pair.rate
        except (Currency.DoesNotExist, CurrencyPair.DoesNotExist):
            gbp_value = None

        if gbp_value:
            total_value_gbp += gbp_value

        holding_list.append({
            "currency": {
                "code": h.currency.code,
                "name": h.currency.name,
                "symbol": h.currency.symbol,
                "flag": h.currency.flag,
            },
            "amount": str(h.amount),
            "avg_buy_rate": str(h.avg_buy_rate),
            "gbp_value": str(round(gbp_value, 2)) if gbp_value is not None else None,
        })

    return Response({
        "holdings": holding_list,
        "total_value_gbp": str(round(total_value_gbp, 2)),
    })


# DASHBOARD API –  GET /dashboard/summary
#               GET /dashboard/market-snapshot

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """
    Stats cards shown on the customer dashboard.
    Returns portfolio value, number of holdings, and 24h P&L placeholder.
    """
    holdings = PortfolioHolding.objects.filter(user=request.user).select_related("currency")
    total_value_gbp = Decimal("0")
    num_currencies = 0

    for h in holdings:
        num_currencies += 1
        try:
            if h.currency.code == "GBP":
                total_value_gbp += h.amount
            else:
                gbp_currency = Currency.objects.get(code="GBP")
                pair = CurrencyPair.objects.get(base=gbp_currency, quote=h.currency)
                total_value_gbp += h.amount / pair.rate
        except (Currency.DoesNotExist, CurrencyPair.DoesNotExist):
            pass

    return Response({
        "portfolio_value_gbp": str(round(total_value_gbp, 2)),
        "num_currencies": num_currencies,
        "change_24h_pct": "0.00",   # placeholder until trade history exists
        "change_24h_gbp": "0.00",   # placeholder until trade history exists
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_market_snapshot(request):
    """
    Top trading pairs for the market snapshot widget on the dashboard.
    Returns up to 10 enabled pairs ordered by base currency code.
    """
    pairs = CurrencyPair.objects.filter(enabled=True).select_related("base", "quote").order_by("base__code")[:10]

    snapshot = [
        {
            "pair": f"{p.base.code}/{p.quote.code}",
            "base_flag": p.base.flag,
            "quote_flag": p.quote.flag,
            "rate": str(p.rate),
            "change_pct": str(p.change_pct),
        }
        for p in pairs
    ]
    return Response({"market_snapshot": snapshot})
