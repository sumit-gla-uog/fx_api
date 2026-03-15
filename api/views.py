from django.shortcuts import render

import csv
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Currency, CurrencyPair, PortfolioHolding, Trade, Order, PriceHistory
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


# Health check API
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})


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


# PAIRS API  GET /pairs?search=

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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pair_latest(request, id):
    """GET /pairs/{id}/latest — current rate for a single pair."""
    try:
        p = CurrencyPair.objects.select_related("base", "quote").get(pk=id, enabled=True)
    except CurrencyPair.DoesNotExist:
        return Response({"error": "pair not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response({"pair": _serialize_pair(p)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pair_history(request, id):
    """
    GET /pairs/{id}/history/?period=1h|1d|1w|1m
    Returns price history for a pair filtered by period.
    """
    try:
        p = CurrencyPair.objects.get(pk=id, enabled=True)
    except CurrencyPair.DoesNotExist:
        return Response({"error": "pair not found"}, status=status.HTTP_404_NOT_FOUND)

    period = request.query_params.get("period", "1d").lower()

    now = timezone.now()
    period_map = {
        "1h": now - timedelta(hours=1),
        "1d": now - timedelta(days=1),
        "1w": now - timedelta(weeks=1),
        "1m": now - timedelta(days=30),
    }
    since = period_map.get(period, period_map["1d"])

    records = PriceHistory.objects.filter(
        pair=p,
        recorded_at__gte=since
    ).order_by("recorded_at")

    # For 1h all points, for longer periods, sample to max 200 points
    max_points = 200
    record_list = list(records)
    if len(record_list) > max_points:
        step = len(record_list) // max_points
        record_list = record_list[::step]

    return Response({
        "pair": f"{p.base.code}/{p.quote.code}",
        "period": period,
        "history": [
            {
                "rate": str(h.rate),
                "recorded_at": h.recorded_at.isoformat(),
            }
            for h in record_list
        ],
    })


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


# DASHBOARD API GET /dashboard/summary
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


# TRADES

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trade_market(request):
    """
    POST /trades/market
    Body: { "pair_id": int, "side": "buy"|"sell", "amount": "100.00" }
    Executes immediately at the current rate and updates the user's portfolio.
    """
    pair_id = request.data.get("pair_id")
    side    = request.data.get("side")
    amount  = request.data.get("amount")

    # Validating my inputs
    if not all([pair_id, side, amount]):
        return Response({"error": "pair_id, side, and amount are required"}, status=status.HTTP_400_BAD_REQUEST)

    if side not in ("buy", "sell"):
        return Response({"error": "side must be 'buy' or 'sell'"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError
    except (ValueError, Exception):
        return Response({"error": "amount must be a positive number"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pair = CurrencyPair.objects.select_related("base", "quote").get(pk=pair_id, enabled=True)
    except CurrencyPair.DoesNotExist:
        return Response({"error": "pair not found"}, status=status.HTTP_404_NOT_FOUND)

    rate  = pair.rate
    total = amount * rate   # how much quote currency isbeing spent/received

    # Recording my trades
    trade = Trade.objects.create(
        user=request.user, pair=pair, side=side,
        amount=amount, rate=rate, total=total,
    )

    #  Updating my portfolio holdings
    _apply_trade_to_portfolio(request.user, pair, side, amount, rate, total)

    return Response({
        "trade": {
            "id":          trade.id,
            "pair":        f"{pair.base.code}/{pair.quote.code}",
            "side":        trade.side,
            "amount":      str(trade.amount),
            "rate":        str(trade.rate),
            "total":       str(trade.total),
            "executed_at": trade.executed_at.isoformat(),
        }
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trades_list(request):
    """GET /trades — list all trades for the authenticated user."""
    trades = Trade.objects.filter(user=request.user).select_related("pair__base", "pair__quote")
    return Response({"trades": [_serialize_trade(t) for t in trades]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trades_export(request):
    """GET /trades/export — download trades as a CSV file."""
    trades = Trade.objects.filter(user=request.user).select_related("pair__base", "pair__quote")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="trades.csv"'

    writer = csv.writer(response)
    writer.writerow(["ID", "Pair", "Side", "Amount", "Rate", "Total", "Executed At"])
    for t in trades:
        writer.writerow([
            t.id,
            f"{t.pair.base.code}/{t.pair.quote.code}",
            t.side,
            t.amount,
            t.rate,
            t.total,
            t.executed_at.isoformat(),
        ])

    return response


# ORDERS

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def order_limit(request):
    """
    POST /orders/limit
    Body: { "pair_id": int, "side": "buy"|"sell", "amount": "100.00", "limit_rate": "1.2500" }
    Creates a limit order (status=open). Filling is handled separately.
    """
    pair_id    = request.data.get("pair_id")
    side       = request.data.get("side")
    amount     = request.data.get("amount")
    limit_rate = request.data.get("limit_rate")

    if not all([pair_id, side, amount, limit_rate]):
        return Response({"error": "pair_id, side, amount, and limit_rate are required"},
                        status=status.HTTP_400_BAD_REQUEST)

    if side not in ("buy", "sell"):
        return Response({"error": "side must be 'buy' or 'sell'"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount     = Decimal(str(amount))
        limit_rate = Decimal(str(limit_rate))
        if amount <= 0 or limit_rate <= 0:
            raise ValueError
    except (ValueError, Exception):
        return Response({"error": "amount and limit_rate must be positive numbers"},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        pair = CurrencyPair.objects.select_related("base", "quote").get(pk=pair_id, enabled=True)
    except CurrencyPair.DoesNotExist:
        return Response({"error": "pair not found"}, status=status.HTTP_404_NOT_FOUND)

    order = Order.objects.create(
        user=request.user, pair=pair, side=side,
        amount=amount, limit_rate=limit_rate, status="open",
    )

    return Response({"order": _serialize_order(order)}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def orders_list(request):
    """GET /orders?status= — list orders, optionally filtered by status."""
    status_filter = request.query_params.get("status", "").strip().lower()
    qs = Order.objects.filter(user=request.user).select_related("pair__base", "pair__quote")

    if status_filter in ("open", "filled", "cancelled"):
        qs = qs.filter(status=status_filter)

    return Response({"orders": [_serialize_order(o) for o in qs]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def order_cancel(request, id):
    """POST /orders/{id}/cancel — cancel an open order."""
    try:
        order = Order.objects.get(pk=id, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "order not found"}, status=status.HTTP_404_NOT_FOUND)

    if order.status != "open":
        return Response({"error": f"cannot cancel an order with status '{order.status}'"},
                        status=status.HTTP_400_BAD_REQUEST)

    order.status = "cancelled"
    order.save()

    return Response({"order": _serialize_order(order)})

# UTIL helper methods, I will move this later in anothor folder - Todo Sumit

def _serialize_pair(p):
    return {
        "id":         p.id,
        "base":       {"code": p.base.code, "name": p.base.name, "symbol": p.base.symbol, "flag": p.base.flag},
        "quote":      {"code": p.quote.code, "name": p.quote.name, "symbol": p.quote.symbol, "flag": p.quote.flag},
        "pair":       f"{p.base.code}/{p.quote.code}",
        "rate":       str(p.rate),
        "change_pct": str(p.change_pct),
    }


def _serialize_trade(t):
    return {
        "id":          t.id,
        "pair":        f"{t.pair.base.code}/{t.pair.quote.code}",
        "side":        t.side,
        "amount":      str(t.amount),
        "rate":        str(t.rate),
        "total":       str(t.total),
        "executed_at": t.executed_at.isoformat(),
    }


def _serialize_order(o):
    return {
        "id":         o.id,
        "pair":       f"{o.pair.base.code}/{o.pair.quote.code}",
        "side":       o.side,
        "amount":     str(o.amount),
        "limit_rate": str(o.limit_rate),
        "status":     o.status,
        "created_at": o.created_at.isoformat(),
        "updated_at": o.updated_at.isoformat(),
    }


def _apply_trade_to_portfolio(user, pair, side, amount, rate, total):
    """Updating my PortfolioHolding rows after a market trade executes."""
    base_currency  = pair.base
    quote_currency = pair.quote

    if side == "buy":
        # User spends quote currency, receives base currency
        _adjust_holding(user, base_currency,  -amount, rate)   # -GBP (kharch kia)
        _adjust_holding(user, quote_currency, +total,  rate)   # +USD (purchase kia)
    else:
        # User sells base currency, receives quote currency
       _adjust_holding(user, base_currency,  +amount, rate)   # +GBP (wapas mila)
       _adjust_holding(user, quote_currency, -total,  rate)   # -USD (diya)


def _adjust_holding(user, currency, delta, rate):
    """Add or subtract from a holding; create if it doesn't exist."""
    holding, _ = PortfolioHolding.objects.get_or_create(
        user=user, currency=currency,
        defaults={"amount": Decimal("0"), "avg_buy_rate": rate},
    )
    holding.amount += delta

     #Never allow amount go below 0
    if holding.amount < 0:
        holding.amount = Decimal("0")

    if delta > 0:
        # Recalculating average buy rate only when buying more
        holding.avg_buy_rate = rate
    holding.save()

