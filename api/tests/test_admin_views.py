import io
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from decimal import Decimal
from api.models import Currency, CurrencyPair
from api.admin_models import ExchangeRate, RateAuditLog

# Base class

class BaseAdminTest(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_user(
            username="admin", password="pass1234", is_staff=True
        )
        self.user = User.objects.create_user(
            username="customer", password="pass1234", is_staff=False
        )
        self.gbp = Currency.objects.create(code="GBP", name="British Pound", symbol="£", enabled=True)
        self.usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$", enabled=True)
        self.pair = CurrencyPair.objects.create(
            base=self.gbp, quote=self.usd,
            rate=Decimal("1.25"), enabled=True
        )

    def login_admin(self):
        self.client.force_authenticate(user=self.admin)

    def login_user(self):
        self.client.force_authenticate(user=self.user)

    def logout(self):
        self.client.force_authenticate(user=None)


# Admin Dashboard

class AdminDashboardTest(BaseAdminTest):

    def test_dashboard_success(self):
        self.login_admin()
        response = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_currencies", response.data)
        self.assertIn("total_pairs", response.data)
        self.assertIn("stale_rates", response.data)

    def test_dashboard_forbidden_for_non_admin(self):
        self.login_user()
        response = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_unauthenticated(self):
        response = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_counts_correct(self):
        self.login_admin()
        response = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(response.data["total_currencies"], 2) # GBP + USD
        self.assertEqual(response.data["total_pairs"], 1) # GBP/USD


# Admin Currencies List

class AdminCurrenciesListTest(BaseAdminTest):

    def test_list_all_currencies(self):
        self.login_admin()
        response = self.client.get(reverse("admin-currencies-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["currencies"]), 2)

    def test_list_includes_disabled_currencies(self):
        self.login_admin()
        self.usd.enabled = False
        self.usd.save()
        response = self.client.get(reverse("admin-currencies-list"))
        # admin sees ALL currencies, even disabled ones
        self.assertEqual(len(response.data["currencies"]), 2)

    def test_list_forbidden_for_non_admin(self):
        self.login_user()
        response = self.client.get(reverse("admin-currencies-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# Admin Currency Add

class AdminCurrencyAddTest(BaseAdminTest):

    def test_add_currency_success(self):
        self.login_admin()
        response = self.client.post(reverse("admin-currency-add"), {
            "code": "EUR",
            "name": "Euro",
            "symbol": "€",
            "flag": "🇪🇺"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["currency"]["code"], "EUR")

    def test_add_currency_missing_fields(self):
        self.login_admin()
        response = self.client.post(reverse("admin-currency-add"), {
            "code": "EUR"
            # missing name and symbol
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_currency_code_too_long(self):
        self.login_admin()
        response = self.client.post(reverse("admin-currency-add"), {
            "code": "TOOLONG",
            "name": "Some Currency",
            "symbol": "X"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_duplicate_currency(self):
        self.login_admin()
        response = self.client.post(reverse("admin-currency-add"), {
            "code": "GBP",  # already exists
            "name": "British Pound",
            "symbol": "£"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", response.data["error"])

    def test_add_currency_auto_creates_pair_with_gbp(self):
        self.login_admin()
        response = self.client.post(reverse("admin-currency-add"), {
            "code": "JPY",
            "name": "Japanese Yen",
            "symbol": "¥"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # GBP/JPY pair should have been auto-created
        self.assertTrue(CurrencyPair.objects.filter(
            base=self.gbp, quote__code="JPY"
        ).exists())

    def test_add_currency_forbidden_for_non_admin(self):
        self.login_user()
        response = self.client.post(reverse("admin-currency-add"), {
            "code": "EUR", "name": "Euro", "symbol": "€"
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# Admin Currency Toggle

class AdminCurrencyToggleTest(BaseAdminTest):

    def test_toggle_disables_enabled_currency(self):
        self.login_admin()
        self.assertTrue(self.usd.enabled)
        response = self.client.patch(reverse("admin-currency-toggle", kwargs={"id": self.usd.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.usd.refresh_from_db()
        self.assertFalse(self.usd.enabled)

    def test_toggle_enables_disabled_currency(self):
        self.login_admin()
        self.usd.enabled = False
        self.usd.save()
        response = self.client.patch(reverse("admin-currency-toggle", kwargs={"id": self.usd.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.usd.refresh_from_db()
        self.assertTrue(self.usd.enabled)

    def test_toggle_nonexistent_currency(self):
        self.login_admin()
        response = self.client.patch(reverse("admin-currency-toggle", kwargs={"id": 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_toggle_forbidden_for_non_admin(self):
        self.login_user()
        response = self.client.patch(reverse("admin-currency-toggle", kwargs={"id": self.usd.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# Admin Rates List

class AdminRatesListTest(BaseAdminTest):

    def setUp(self):
        super().setUp()
        ExchangeRate.objects.create(
            pair=self.pair, rate=Decimal("1.27"),
            source="manual", updated_by=self.admin
        )

    def test_rates_list_success(self):
        self.login_admin()
        response = self.client.get(reverse("admin-rates-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["rates"]), 1)
        self.assertEqual(response.data["rates"][0]["pair"], "GBP/USD")

    def test_rates_list_forbidden_for_non_admin(self):
        self.login_user()
        response = self.client.get(reverse("admin-rates-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# Admin Rate Manual Update

class AdminRateManualTest(BaseAdminTest):

    def test_manual_rate_update_success(self):
        self.login_admin()
        response = self.client.post(reverse("admin-rate-manual"), {
            "pair_id": self.pair.id,
            "rate": "1.30"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.rate, Decimal("1.30"))

    def test_manual_rate_creates_exchange_rate_record(self):
        self.login_admin()
        self.client.post(reverse("admin-rate-manual"), {
            "pair_id": self.pair.id,
            "rate": "1.30"
        })
        self.assertEqual(ExchangeRate.objects.count(), 1)
        self.assertEqual(ExchangeRate.objects.first().source, "manual")

    def test_manual_rate_creates_audit_log(self):
        self.login_admin()
        self.client.post(reverse("admin-rate-manual"), {
            "pair_id": self.pair.id,
            "rate": "1.30"
        })
        self.assertEqual(RateAuditLog.objects.count(), 1)
        log = RateAuditLog.objects.first()
        self.assertEqual(log.old_rate, Decimal("1.25"))
        self.assertEqual(log.new_rate, Decimal("1.30"))

    def test_manual_rate_missing_fields(self):
        self.login_admin()
        response = self.client.post(reverse("admin-rate-manual"), {"pair_id": self.pair.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_rate_invalid_rate(self):
        self.login_admin()
        response = self.client.post(reverse("admin-rate-manual"), {
            "pair_id": self.pair.id,
            "rate": "abc"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_rate_negative_rate(self):
        self.login_admin()
        response = self.client.post(reverse("admin-rate-manual"), {
            "pair_id": self.pair.id,
            "rate": "-1.5"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_rate_pair_not_found(self):
        self.login_admin()
        response = self.client.post(reverse("admin-rate-manual"), {
            "pair_id": 9999,
            "rate": "1.30"
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manual_rate_forbidden_for_non_admin(self):
        self.login_user()
        response = self.client.post(reverse("admin-rate-manual"), {
            "pair_id": self.pair.id, "rate": "1.30"
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# Admin Rate CSV Upload

class AdminRateCSVTest(BaseAdminTest):

    def make_csv(self, content):
        """Helper to create an in-memory CSV file"""
        return io.BytesIO(content.encode("utf-8")), "rates.csv"

    def test_csv_upload_success(self):
        self.login_admin()
        csv_content = "pair_code,rate\nGBP/USD,1.30\n"
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "rates.csv"
        response = self.client.post(
            reverse("admin-rate-csv"),
            {"file": csv_file},
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"], 1)
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.rate, Decimal("1.30"))

    def test_csv_upload_no_file(self):
        self.login_admin()
        response = self.client.post(reverse("admin-rate-csv"), {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_csv_upload_invalid_extension(self):
        self.login_admin()
        txt_file = io.BytesIO(b"pair_code,rate\nGBP/USD,1.30\n")
        txt_file.name = "rates.txt"
        response = self.client.post(
            reverse("admin-rate-csv"),
            {"file": txt_file},
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_csv_upload_invalid_rate(self):
        self.login_admin()
        csv_file = io.BytesIO(b"pair_code,rate\nGBP/USD,bad_rate\n")
        csv_file.name = "rates.csv"
        response = self.client.post(
            reverse("admin-rate-csv"),
            {"file": csv_file},
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"], 0)
        self.assertEqual(len(response.data["errors"]), 1)

    def test_csv_upload_pair_not_found(self):
        self.login_admin()
        csv_file = io.BytesIO(b"pair_code,rate\nXXX/YYY,1.50\n")
        csv_file.name = "rates.csv"
        response = self.client.post(
            reverse("admin-rate-csv"),
            {"file": csv_file},
            format="multipart"
        )
        self.assertEqual(response.data["updated"], 0)
        self.assertEqual(len(response.data["errors"]), 1)

    def test_csv_upload_creates_audit_logs(self):
        self.login_admin()
        csv_file = io.BytesIO(b"pair_code,rate\nGBP/USD,1.30\n")
        csv_file.name = "rates.csv"
        self.client.post(
            reverse("admin-rate-csv"),
            {"file": csv_file},
            format="multipart"
        )
        self.assertEqual(RateAuditLog.objects.count(), 1)
        self.assertEqual(RateAuditLog.objects.first().source, "csv")

    def test_csv_upload_forbidden_for_non_admin(self):
        self.login_user()
        csv_file = io.BytesIO(b"pair_code,rate\nGBP/USD,1.30\n")
        csv_file.name = "rates.csv"
        response = self.client.post(
            reverse("admin-rate-csv"),
            {"file": csv_file},
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)