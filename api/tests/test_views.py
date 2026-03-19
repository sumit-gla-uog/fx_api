from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from api.models import Currency, CurrencyPair, PortfolioHolding, Trade, Order


# Base class, shared setup for all view tests

class BaseAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Create a regular user
        self.user = User.objects.create_user(username="testuser", password="pass1234")

        # Create an admin user
        self.admin = User.objects.create_user(username="adminuser", password="pass1234", is_staff=True)

        # Create currencies
        self.gbp = Currency.objects.create(code="GBP", name="British Pound", symbol="£", enabled=True)
        self.usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$", enabled=True)

        # Create a currency pair GBP/USD
        self.pair = CurrencyPair.objects.create(
            base=self.gbp,
            quote=self.usd,
            rate=Decimal("1.25"),
            enabled=True
        )

    def login(self, user=None):
        """Force authenticate a user"""
        self.client.force_authenticate(user=user or self.user)

    def logout(self):
        self.client.force_authenticate(user=None)


# Health Check

class HealthCheckTest(BaseAPITest):

    def test_health_check_returns_ok(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")


# Auth - Signup

class SignupViewTest(BaseAPITest):

    def test_signup_success(self):
        response = self.client.post(reverse("auth-signup"), {
            "username": "newuser",
            "password": "pass1234"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["ok"])

    def test_signup_missing_username(self):
        response = self.client.post(reverse("auth-signup"), {
            "password": "pass1234"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_signup_missing_password(self):
        response = self.client.post(reverse("auth-signup"), {
            "username": "newuser"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_duplicate_username(self):
        response = self.client.post(reverse("auth-signup"), {
            "username": "testuser",  # already exists in setUp
            "password": "pass1234"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", response.data["error"])

    def test_signup_admin_role(self):
        response = self.client.post(reverse("auth-signup"), {
            "username": "newadmin",
            "password": "pass1234",
            "role": "admin"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.get(username="newadmin").is_staff)


# Auth - Me

class MeViewTest(BaseAPITest):

    def test_me_returns_user_info(self):
        self.login()
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "testuser")
        self.assertEqual(response.data["user"]["role"], "customer")

    def test_me_admin_role(self):
        self.login(self.admin)
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.data["user"]["role"], "admin")

    def test_me_unauthenticated(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

# Currencies List

class CurrenciesListViewTest(BaseAPITest):

    def test_currencies_list_returns_enabled_only(self):
        self.login()
        # Disable USD
        self.usd.enabled = False
        self.usd.save()
        response = self.client.get(reverse("currencies-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = [c["code"] for c in response.data["currencies"]]
        self.assertIn("GBP", codes)
        self.assertNotIn("USD", codes)

    def test_currencies_list_search(self):
        self.login()
        response = self.client.get(reverse("currencies-list"), {"search": "GBP"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["currencies"]), 1)
        self.assertEqual(response.data["currencies"][0]["code"], "GBP")

    def test_currencies_list_unauthenticated(self):
        response = self.client.get(reverse("currencies-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# Pairs List

class PairsListViewTest(BaseAPITest):

    def test_pairs_list_success(self):
        self.login()
        response = self.client.get(reverse("pairs-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["pairs"]), 1)
        self.assertEqual(response.data["pairs"][0]["pair"], "GBP/USD")

    def test_pairs_list_search(self):
        self.login()
        response = self.client.get(reverse("pairs-list"), {"search": "GBP"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["pairs"]), 1)

    def test_pairs_list_unauthenticated(self):
        response = self.client.get(reverse("pairs-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# Portfolio Deposit

class PortfolioDepositViewTest(BaseAPITest):

    def valid_payload(self, amount="500.00"):
        return {
            "amount": amount,
            "bank_name": "HSBC",
            "account_number": "12345678",
            "sort_code": "12-34-56"
        }

    def test_deposit_success(self):
        self.login()
        response = self.client.post(reverse("portfolio-deposit"), self.valid_payload())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["ok"])
        self.assertEqual(response.data["deposit"]["amount"], "500.00")

    def test_deposit_missing_amount(self):
        self.login()
        payload = self.valid_payload()
        del payload["amount"]
        response = self.client.post(reverse("portfolio-deposit"), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_invalid_amount(self):
        self.login()
        response = self.client.post(reverse("portfolio-deposit"), self.valid_payload(amount="abc"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_negative_amount(self):
        self.login()
        response = self.client.post(reverse("portfolio-deposit"), self.valid_payload(amount="-100"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_exceeds_max(self):
        self.login()
        response = self.client.post(reverse("portfolio-deposit"), self.valid_payload(amount="200000"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_invalid_account_number(self):
        self.login()
        payload = self.valid_payload()
        payload["account_number"] = "123"  # not 8 digits
        response = self.client.post(reverse("portfolio-deposit"), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_invalid_sort_code(self):
        self.login()
        payload = self.valid_payload()
        payload["sort_code"] = "123456"  # wrong format
        response = self.client.post(reverse("portfolio-deposit"), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_unauthenticated(self):
        response = self.client.post(reverse("portfolio-deposit"), self.valid_payload())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_deposit_increases_balance(self):
        self.login()
        self.client.post(reverse("portfolio-deposit"), self.valid_payload(amount="300.00"))
        self.client.post(reverse("portfolio-deposit"), self.valid_payload(amount="200.00"))
        holding = PortfolioHolding.objects.get(user=self.user, currency=self.gbp)
        self.assertEqual(holding.amount, Decimal("500.00"))


# Trade Market

class TradeMarketViewTest(BaseAPITest):

    def setUp(self):
        super().setUp()
        # Give user some GBP and USD to trade with
        PortfolioHolding.objects.create(
            user=self.user, currency=self.gbp,
            amount=Decimal("1000.00"), avg_buy_rate=Decimal("1")
        )
        PortfolioHolding.objects.create(
            user=self.user, currency=self.usd,
            amount=Decimal("1000.00"), avg_buy_rate=Decimal("1")
        )

    def test_trade_buy_success(self):
        self.login()
        response = self.client.post(reverse("trade-market"), {
            "pair_id": self.pair.id,
            "side": "buy",
            "amount": "100.00"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("trade", response.data)
        self.assertEqual(response.data["trade"]["side"], "buy")

    def test_trade_sell_success(self):
        self.login()
        response = self.client.post(reverse("trade-market"), {
            "pair_id": self.pair.id,
            "side": "sell",
            "amount": "50.00"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["trade"]["side"], "sell")

    def test_trade_missing_fields(self):
        self.login()
        response = self.client.post(reverse("trade-market"), {"pair_id": self.pair.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_trade_invalid_side(self):
        self.login()
        response = self.client.post(reverse("trade-market"), {
            "pair_id": self.pair.id,
            "side": "hold",  # invalid
            "amount": "100"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_trade_invalid_pair(self):
        self.login()
        response = self.client.post(reverse("trade-market"), {
            "pair_id": 9999,  # doesn't exist
            "side": "buy",
            "amount": "100"
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_trade_unauthenticated(self):
        response = self.client.post(reverse("trade-market"), {
            "pair_id": self.pair.id, "side": "buy", "amount": "100"
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

# Orders

class OrderViewTest(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.order = Order.objects.create(
            user=self.user, pair=self.pair,
            side="buy", amount=Decimal("100"),
            limit_rate=Decimal("1.20"), status="open"
        )

    def test_create_limit_order_success(self):
        self.login()
        response = self.client.post(reverse("order-limit"), {
            "pair_id": self.pair.id,
            "side": "buy",
            "amount": "200",
            "limit_rate": "1.30"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["order"]["status"], "open")

    def test_create_order_missing_fields(self):
        self.login()
        response = self.client.post(reverse("order-limit"), {"pair_id": self.pair.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_invalid_side(self):
        self.login()
        response = self.client.post(reverse("order-limit"), {
            "pair_id": self.pair.id,
            "side": "hold",
            "amount": "100",
            "limit_rate": "1.20"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_orders_list(self):
        self.login()
        response = self.client.get(reverse("orders-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["orders"]), 1)

    def test_orders_list_filter_by_status(self):
        self.login()
        response = self.client.get(reverse("orders-list"), {"status": "open"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["orders"]), 1)

    def test_cancel_order_success(self):
        self.login()
        response = self.client.post(reverse("order-cancel", kwargs={"id": self.order.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order"]["status"], "cancelled")

    def test_cancel_already_cancelled_order(self):
        self.login()
        self.order.status = "cancelled"
        self.order.save()
        response = self.client.post(reverse("order-cancel", kwargs={"id": self.order.id}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_nonexistent_order(self):
        self.login()
        response = self.client.post(reverse("order-cancel", kwargs={"id": 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)