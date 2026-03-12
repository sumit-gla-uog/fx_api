from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Currency(models.Model):
    """Master list of currencies (seeded with 10 for Sprint 1)."""

    code = models.CharField(max_length=3, unique=True)  # e.g., GBP
    name = models.CharField(max_length=64)              # e.g., British Pound
    flag = models.CharField(max_length=2, blank=True)       # e.g., GB (for UI flag column)
    symbol = models.CharField(max_length=8, blank=True) # e.g., £
    is_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_enabled"]),
        ]

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.code


class CurrencyPair(models.Model):
    """Tradable FX pair (base -> quote)."""

    base_currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="pairs_as_base"
    )
    quote_currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="pairs_as_quote"
    )
    is_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["base_currency__code", "quote_currency__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["base_currency", "quote_currency"],
                name="uniq_currency_pair_base_quote",
            ),
            models.CheckConstraint(
                check=~Q(base_currency=models.F("quote_currency")),
                name="chk_base_not_equal_quote",
            ),
        ]
        indexes = [
            models.Index(fields=["is_enabled"]),
            models.Index(fields=["base_currency", "quote_currency"]),
        ]

    @property
    def code(self) -> str:
        return f"{self.base_currency.code}/{self.quote_currency.code}"

    def __str__(self) -> str:
        return self.code


class PortfolioHolding(models.Model):
    """User wallet balances across multiple currencies."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolio_holdings"
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="holdings"
    )
    amount = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id", "currency__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "currency"],
                name="uniq_holding_user_currency",
            ),
            models.CheckConstraint(
                check=Q(amount__gte=0),
                name="chk_holding_amount_nonnegative",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "currency"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.currency.code}={self.amount}"

    class ExchangeRate(models.Model):
        """
        Historical FX rate for a given CurrencyPair.
        rate = quote per 1 base (e.g., GBP/USD rate=1.25 means 1 GBP = 1.25 USD)
        """

        class Source(models.TextChoices):
            API = "api", "API"
            MANUAL = "manual", "MANUAL"
            CSV = "csv", "CSV"

        pair = models.ForeignKey(CurrencyPair, on_delete=models.PROTECT, related_name="rates")
        rate = models.DecimalField(max_digits=20, decimal_places=6)
        as_of = models.DateTimeField(default=timezone.now)
        source = models.CharField(
            max_length=16,
            choices=Source.choices,
            default=Source.API
        )

        created_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ["-as_of"]
            constraints = [
                models.UniqueConstraint(fields=["pair", "as_of"], name="uniq_rate_pair_asof")
            ]
            indexes = [
                models.Index(fields=["pair", "-as_of"]),
            ]

        def __str__(self) -> str:
            return f"{self.pair.code}@{self.as_of:%Y-%m-%d %H:%M}={self.rate}"

    class Trade(models.Model):
        class Side(models.TextChoices):
            BUY = "BUY", "BUY"  # buy base using quote
            SELL = "SELL", "SELL"  # sell base for quote

        class Status(models.TextChoices):
            EXECUTED = "EXECUTED", "EXECUTED"
            FAILED = "FAILED", "FAILED"

        user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trades")
        pair = models.ForeignKey(CurrencyPair, on_delete=models.PROTECT, related_name="trades")
        side = models.CharField(max_length=4, choices=Side.choices)

        amount_base = models.DecimalField(max_digits=20, decimal_places=6)  # executed base amount
        rate = models.DecimalField(max_digits=20, decimal_places=6)  # execution rate snapshot
        amount_quote = models.DecimalField(max_digits=20, decimal_places=6)  # amount_base * rate snapshot

        status = models.CharField(max_length=16, choices=Status.choices, default=Status.EXECUTED)
        executed_at = models.DateTimeField(default=timezone.now)

        created_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ["-executed_at"]
            indexes = [
                models.Index(fields=["user", "-executed_at"]),
                models.Index(fields=["pair", "-executed_at"]),
            ]

        def __str__(self) -> str:
            return f"{self.user_id} {self.side} {self.pair.code} {self.amount_base}@{self.rate} ({self.status})"

    class LimitOrder(models.Model):
        class Side(models.TextChoices):
            BUY = "BUY", "BUY"  # buy base using quote
            SELL = "SELL", "SELL"  # sell base for quote

        class Status(models.TextChoices):
            PENDING = "PENDING", "PENDING"
            EXECUTED = "EXECUTED", "EXECUTED"
            CANCELLED = "CANCELLED", "CANCELLED"

        user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="limit_orders")
        pair = models.ForeignKey(CurrencyPair, on_delete=models.PROTECT, related_name="limit_orders")
        side = models.CharField(max_length=4, choices=Side.choices)

        amount_base = models.DecimalField(max_digits=20, decimal_places=6)
        limit_rate = models.DecimalField(max_digits=20, decimal_places=6)

        status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)
        executed_at = models.DateTimeField(null=True, blank=True)

        class Meta:
            ordering = ["-created_at"]
            indexes = [
                models.Index(fields=["user", "status", "-created_at"]),
                models.Index(fields=["pair", "status", "-created_at"]),
            ]

        def __str__(self) -> str:
            return f"{self.user_id} {self.side} {self.pair.code} {self.amount_base}@{self.limit_rate} ({self.status})"

    # ---- Sprint 2: portfolio update helper (minimal, called by service layer) ----
    class InsufficientBalance(Exception):
        pass

    def get_holding_for_update(user, currency):
        """
        Used inside transaction.atomic() to lock the holding row.
        Creates holding row if missing.
        """
        holding, _ = PortfolioHolding.objects.select_for_update().get_or_create(
            user=user, currency=currency, defaults={"amount": Decimal("0")}
        )
        return holding

    class RateAuditLog(models.Model):
        class Action(models.TextChoices):
            CREATED = "CREATED", "CREATED"
            UPDATED = "UPDATED", "UPDATED"
            IMPORTED = "IMPORTED", "IMPORTED"

        pair = models.ForeignKey(CurrencyPair, on_delete=models.PROTECT, related_name="rate_audit_logs")
        rate = models.DecimalField(max_digits=20, decimal_places=6)
        source = models.CharField(
            max_length=16,
            choices=ExchangeRate.Source.choices
        )
        action = models.CharField(
            max_length=16,
            choices=Action.choices,
            default=Action.UPDATED
        )
        changed_by = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="rate_audit_logs"
        )
        note = models.CharField(max_length=255, blank=True)
        created_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ["-created_at"]
            indexes = [
                models.Index(fields=["pair", "-created_at"]),
                models.Index(fields=["source", "-created_at"]),
            ]

        def __str__(self) -> str:
            return f"{self.pair.code} {self.action} {self.rate} ({self.source})"

        class APIHealthStatus(models.Model):
            class Status(models.TextChoices):
                UP = "UP", "UP"
                DOWN = "DOWN", "DOWN"
                DEGRADED = "DEGRADED", "DEGRADED"
                UNKNOWN = "UNKNOWN", "UNKNOWN"

            provider_name = models.CharField(max_length=64, unique=True)
            endpoint = models.URLField(blank=True)
            status = models.CharField(
                max_length=16,
                choices=Status.choices,
                default=Status.UNKNOWN
            )
            status_code = models.IntegerField(null=True, blank=True)
            response_time_ms = models.IntegerField(null=True, blank=True)
            message = models.CharField(max_length=255, blank=True)
            checked_at = models.DateTimeField(null=True, blank=True)
            updated_at = models.DateTimeField(auto_now=True)

            class Meta:
                ordering = ["provider_name"]

            def __str__(self) -> str:
                return f"{self.provider_name} - {self.status}"

            class UserProfile(models.Model):
                class Role(models.TextChoices):
                    CUSTOMER = "CUSTOMER", "CUSTOMER"
                    ADMIN = "ADMIN", "ADMIN"

                user = models.OneToOneField(
                    settings.AUTH_USER_MODEL,
                    on_delete=models.CASCADE,
                    related_name="profile"
                )
                role = models.CharField(
                    max_length=16,
                    choices=Role.choices,
                    default=Role.CUSTOMER
                )
                created_at = models.DateTimeField(auto_now_add=True)

                def __str__(self) -> str:
                    return f"{self.user.username} - {self.role}"