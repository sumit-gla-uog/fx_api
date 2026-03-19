from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from api.models import Currency, CurrencyPair, PortfolioHolding, PriceHistory, Trade, Order


# Helpers

def make_user(username="testuser"):
    return User.objects.create_user(username=username, password="pass1234")

def make_currency(code="USD", name="US Dollar", symbol="$"):
    return Currency.objects.create(code=code, name=name, symbol=symbol)

def make_pair(base, quote, rate="1.25"):
    return CurrencyPair.objects.create(base=base, quote=quote, rate=Decimal(rate))


# Currency Tests

class CurrencyModelTest(TestCase):

    def setUp(self):
        self.currency = make_currency()

    def test_currency_created_successfully(self):
        self.assertEqual(self.currency.code, "USD")
        self.assertEqual(self.currency.name, "US Dollar")
        self.assertEqual(self.currency.symbol, "$")

    def test_currency_str(self):
        self.assertEqual(str(self.currency), "USD")

    def test_currency_enabled_default_is_true(self):
        self.assertTrue(self.currency.enabled)

    def test_currency_flag_can_be_blank(self):
        c = make_currency(code="GBP", name="British Pound", symbol="£")
        self.assertEqual(c.flag, "")

    def test_currency_code_is_unique(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            make_currency(code="USD")  # duplicate


# CurrencyPair Tests

class CurrencyPairModelTest(TestCase):

    def setUp(self):
        self.usd = make_currency(code="USD", name="US Dollar", symbol="$")
        self.eur = make_currency(code="EUR", name="Euro", symbol="€")
        self.pair = make_pair(self.usd, self.eur)

    def test_pair_created_successfully(self):
        self.assertEqual(self.pair.base, self.usd)
        self.assertEqual(self.pair.quote, self.eur)
        self.assertEqual(self.pair.rate, Decimal("1.25"))

    def test_pair_str(self):
        self.assertEqual(str(self.pair), "USD/EUR")

    def test_pair_enabled_default_is_true(self):
        self.assertTrue(self.pair.enabled)

    def test_pair_change_pct_default_is_zero(self):
        self.assertEqual(self.pair.change_pct, Decimal("0"))

    def test_pair_unique_together(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            make_pair(self.usd, self.eur)  # duplicate base+quote


# PortfolioHolding Tests

class PortfolioHoldingModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.currency = make_currency()
        self.holding = PortfolioHolding.objects.create(
            user=self.user,
            currency=self.currency,
            amount=Decimal("500.00"),
            avg_buy_rate=Decimal("1.20")
        )

    def test_holding_created_successfully(self):
        self.assertEqual(self.holding.user, self.user)
        self.assertEqual(self.holding.currency, self.currency)
        self.assertEqual(self.holding.amount, Decimal("500.00"))

    def test_holding_str(self):
        self.assertEqual(str(self.holding), "testuser - USD")

    def test_holding_avg_buy_rate_default(self):
        holding = PortfolioHolding.objects.create(
            user=make_user(username="user2"),
            currency=self.currency,
            amount=Decimal("100.00")
        )
        self.assertEqual(holding.avg_buy_rate, Decimal("1"))

    def test_holding_unique_together(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            PortfolioHolding.objects.create(
                user=self.user,
                currency=self.currency,  # duplicate user+currency
                amount=Decimal("999.00")
            )


# PriceHistory Tests

class PriceHistoryModelTest(TestCase):

    def setUp(self):
        self.usd = make_currency(code="USD", name="US Dollar", symbol="$")
        self.eur = make_currency(code="EUR", name="Euro", symbol="€")
        self.pair = make_pair(self.usd, self.eur)
        self.now = timezone.now()
        self.history = PriceHistory.objects.create(
            pair=self.pair,
            rate=Decimal("1.25"),
            recorded_at=self.now
        )

    def test_history_created_successfully(self):
        self.assertEqual(self.history.pair, self.pair)
        self.assertEqual(self.history.rate, Decimal("1.25"))

    def test_history_str(self):
        expected = f"USD/EUR @ 1.25 ({self.now})"
        self.assertEqual(str(self.history), expected)

    def test_history_ordering_latest_first(self):
        older = PriceHistory.objects.create(
            pair=self.pair,
            rate=Decimal("1.20"),
            recorded_at=timezone.now() - timezone.timedelta(days=1)
        )
        first = PriceHistory.objects.first()
        self.assertEqual(first, self.history)  # newer should come first


# Trade Tests

class TradeModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.usd = make_currency(code="USD", name="US Dollar", symbol="$")
        self.eur = make_currency(code="EUR", name="Euro", symbol="€")
        self.pair = make_pair(self.usd, self.eur)
        self.trade = Trade.objects.create(
            user=self.user,
            pair=self.pair,
            side="buy",
            amount=Decimal("100.00"),
            rate=Decimal("1.25"),
            total=Decimal("125.00")
        )

    def test_trade_created_successfully(self):
        self.assertEqual(self.trade.user, self.user)
        self.assertEqual(self.trade.side, "buy")
        self.assertEqual(self.trade.amount, Decimal("100.00"))
        self.assertEqual(self.trade.total, Decimal("125.00"))

    def test_trade_str(self):
        self.assertEqual(
            str(self.trade),
            "testuser buy 100.00 USD/EUR @ 1.25"
        )

    def test_trade_executed_at_auto_set(self):
        self.assertIsNotNone(self.trade.executed_at)

    def test_trade_sell_side(self):
        trade = Trade.objects.create(
            user=self.user,
            pair=self.pair,
            side="sell",
            amount=Decimal("50.00"),
            rate=Decimal("1.25"),
            total=Decimal("62.50")
        )
        self.assertEqual(trade.side, "sell")


# Order Tests

class OrderModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.usd = make_currency(code="USD", name="US Dollar", symbol="$")
        self.eur = make_currency(code="EUR", name="Euro", symbol="€")
        self.pair = make_pair(self.usd, self.eur)
        self.order = Order.objects.create(
            user=self.user,
            pair=self.pair,
            side="buy",
            amount=Decimal("200.00"),
            limit_rate=Decimal("1.20")
        )

    def test_order_created_successfully(self):
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.side, "buy")
        self.assertEqual(self.order.amount, Decimal("200.00"))
        self.assertEqual(self.order.limit_rate, Decimal("1.20"))

    def test_order_status_default_is_open(self):
        self.assertEqual(self.order.status, "open")

    def test_order_str(self):
        self.assertEqual(
            str(self.order),
            "testuser buy 200.00 USD/EUR limit@1.20 [open]"
        )

    def test_order_status_can_be_filled(self):
        self.order.status = "filled"
        self.order.save()
        self.assertEqual(self.order.status, "filled")

    def test_order_status_can_be_cancelled(self):
        self.order.status = "cancelled"
        self.order.save()
        self.assertEqual(self.order.status, "cancelled")

    def test_order_timestamps_auto_set(self):
        self.assertIsNotNone(self.order.created_at)
        self.assertIsNotNone(self.order.updated_at)