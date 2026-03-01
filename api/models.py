from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q


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
