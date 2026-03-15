from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone

from api.models import CurrencyPair, ExchangeRate, Trade, PortfolioHolding, InsufficientBalance, get_holding_for_update


def _quant6(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def get_latest_rate(pair: CurrencyPair) -> ExchangeRate:
    rate = ExchangeRate.objects.filter(pair=pair).order_by("-as_of").first()
    if not rate:
        raise ValueError(f"No ExchangeRate found for pair {pair.code}. Seed Sprint2 rates first.")
    return rate


@transaction.atomic
def execute_market_trade(*, user, pair: CurrencyPair, side: str, amount_base: Decimal) -> Trade:
    """
    Executes a market trade and updates PortfolioHolding immediately (Sprint2 requirement).
    side = 'BUY' or 'SELL' (BUY/SELL base currency of the pair)
    amount_base = executed base amount
    """
    amount_base = _quant6(Decimal(amount_base))
    if amount_base <= 0:
        raise ValueError("amount_base must be > 0")

    latest = get_latest_rate(pair)
    rate = _quant6(latest.rate)
    amount_quote = _quant6(amount_base * rate)

    base_ccy = pair.base_currency
    quote_ccy = pair.quote_currency

    # lock holdings rows
    base_h = get_holding_for_update(user, base_ccy)
    quote_h = get_holding_for_update(user, quote_ccy)

    side = side.upper()
    if side == Trade.Side.BUY:
        # pay quote, receive base
        if quote_h.amount < amount_quote:
            raise InsufficientBalance(f"Not enough {quote_ccy.code}. need={amount_quote} have={quote_h.amount}")
        quote_h.amount = _quant6(quote_h.amount - amount_quote)
        base_h.amount = _quant6(base_h.amount + amount_base)

    elif side == Trade.Side.SELL:
        # sell base, receive quote
        if base_h.amount < amount_base:
            raise InsufficientBalance(f"Not enough {base_ccy.code}. need={amount_base} have={base_h.amount}")
        base_h.amount = _quant6(base_h.amount - amount_base)
        quote_h.amount = _quant6(quote_h.amount + amount_quote)

    else:
        raise ValueError("side must be BUY or SELL")

    # persist holdings
    quote_h.save(update_fields=["amount", "updated_at"])
    base_h.save(update_fields=["amount", "updated_at"])

    # create trade record
    trade = Trade.objects.create(
        user=user,
        pair=pair,
        side=side,
        amount_base=amount_base,
        rate=rate,
        amount_quote=amount_quote,
        status=Trade.Status.EXECUTED,
        executed_at=timezone.now(),
    )
    return trade