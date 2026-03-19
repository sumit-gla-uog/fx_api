from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from api.models import Currency, CurrencyPair
from api.admin_models import ExchangeRate, RateAuditLog


# Helpers

def make_user(username="admin", is_staff=True):
    return User.objects.create_user(username=username, password="pass1234", is_staff=is_staff)

def make_currency(code="GBP", name="British Pound", symbol="£"):
    return Currency.objects.create(code=code, name=name, symbol=symbol, enabled=True)

def make_pair(base, quote, rate="1.25"):
    return CurrencyPair.objects.create(base=base, quote=quote, rate=Decimal(rate), enabled=True)


# ExchangeRate Model Tests

class ExchangeRateModelTest(TestCase):

    def setUp(self):
        self.admin = make_user()
        self.gbp = make_currency(code="GBP", name="British Pound", symbol="£")
        self.usd = make_currency(code="USD", name="US Dollar", symbol="$")
        self.pair = make_pair(self.gbp, self.usd)
        self.rate = ExchangeRate.objects.create(
            pair=self.pair,
            rate=Decimal("1.27"),
            source="manual",
            updated_by=self.admin
        )

    def test_exchange_rate_created_successfully(self):
        self.assertEqual(self.rate.pair, self.pair)
        self.assertEqual(self.rate.rate, Decimal("1.27"))
        self.assertEqual(self.rate.source, "manual")
        self.assertEqual(self.rate.updated_by, self.admin)

    def test_exchange_rate_source_default_is_api(self):
        rate = ExchangeRate.objects.create(
            pair=self.pair,
            rate=Decimal("1.30"),
        )
        self.assertEqual(rate.source, "api")

    def test_exchange_rate_updated_by_can_be_null(self):
        rate = ExchangeRate.objects.create(
            pair=self.pair,
            rate=Decimal("1.30"),
            updated_by=None
        )
        self.assertIsNone(rate.updated_by)

    def test_exchange_rate_as_of_auto_set(self):
        self.assertIsNotNone(self.rate.as_of)

    def test_exchange_rate_str(self):
        result = str(self.rate)
        self.assertIn("GBP/USD", result)
        self.assertIn("manual", result)

    def test_exchange_rate_ordering_latest_first(self):
        rate2 = ExchangeRate.objects.create(pair=self.pair, rate=Decimal("1.30"))
        first = ExchangeRate.objects.first()
        self.assertEqual(first, rate2)  # newer should come first

    def test_exchange_rate_cascade_delete_with_pair(self):
        self.pair.delete()
        self.assertEqual(ExchangeRate.objects.count(), 0)


# RateAuditLog Model Tests

class RateAuditLogModelTest(TestCase):

    def setUp(self):
        self.admin = make_user()
        self.gbp = make_currency(code="GBP", name="British Pound", symbol="£")
        self.usd = make_currency(code="USD", name="US Dollar", symbol="$")
        self.pair = make_pair(self.gbp, self.usd)
        self.log = RateAuditLog.objects.create(
            pair=self.pair,
            old_rate=Decimal("1.25"),
            new_rate=Decimal("1.27"),
            source="manual",
            action="updated",
            changed_by=self.admin
        )

    def test_audit_log_created_successfully(self):
        self.assertEqual(self.log.pair, self.pair)
        self.assertEqual(self.log.old_rate, Decimal("1.25"))
        self.assertEqual(self.log.new_rate, Decimal("1.27"))
        self.assertEqual(self.log.action, "updated")
        self.assertEqual(self.log.changed_by, self.admin)

    def test_audit_log_old_rate_can_be_null(self):
        log = RateAuditLog.objects.create(
            pair=self.pair,
            old_rate=None,
            new_rate=Decimal("1.27"),
            action="created",
            changed_by=self.admin
        )
        self.assertIsNone(log.old_rate)

    def test_audit_log_changed_by_can_be_null(self):
        log = RateAuditLog.objects.create(
            pair=self.pair,
            new_rate=Decimal("1.27"),
            changed_by=None
        )
        self.assertIsNone(log.changed_by)

    def test_audit_log_note_can_be_blank(self):
        self.assertEqual(self.log.note, "")

    def test_audit_log_default_action_is_updated(self):
        log = RateAuditLog.objects.create(
            pair=self.pair,
            new_rate=Decimal("1.30"),
        )
        self.assertEqual(log.action, "updated")

    def test_audit_log_default_source_is_manual(self):
        log = RateAuditLog.objects.create(
            pair=self.pair,
            new_rate=Decimal("1.30"),
        )
        self.assertEqual(log.source, "manual")

    def test_audit_log_str(self):
        result = str(self.log)
        self.assertIn("GBP/USD", result)
        self.assertIn("updated", result)
        self.assertIn("1.25", result)
        self.assertIn("1.27", result)

    def test_audit_log_ordering_latest_first(self):
        log2 = RateAuditLog.objects.create(
            pair=self.pair,
            new_rate=Decimal("1.30"),
            action="updated"
        )
        first = RateAuditLog.objects.first()
        self.assertEqual(first, log2)

    def test_audit_log_cascade_delete_with_pair(self):
        self.pair.delete()
        self.assertEqual(RateAuditLog.objects.count(), 0)