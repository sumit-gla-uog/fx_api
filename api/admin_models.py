from django.db import models
from django.contrib.auth.models import User
from .models import CurrencyPair


class ExchangeRate(models.Model):
    """
    Stores rate updates for a currency pair.
    Created whenever admin manually updates or imports a rate.
    rate = quote per 1 base (e.g. GBP/USD rate=1.27 means 1 GBP = 1.27 USD)
    """

    SOURCE_CHOICES = [
        ("api",    "API"),
        ("manual", "Manual"),
        ("csv",    "CSV Import"),
    ]

    pair       = models.ForeignKey(CurrencyPair, on_delete=models.CASCADE, related_name="exchange_rates")
    rate       = models.DecimalField(max_digits=20, decimal_places=6)
    source     = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="api")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="rate_updates")
    as_of      = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'api'
        ordering = ["-as_of"]

    def __str__(self):
        return f"{self.pair} = {self.rate} ({self.source}) @ {self.as_of:%Y-%m-%d %H:%M}"


class RateAuditLog(models.Model):
    """
    Audit trail — every time a rate changes, one row is written here.
    Useful for admin to see who changed what and when.
    """

    ACTION_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("csv",     "CSV Import"),
    ]

    pair       = models.ForeignKey(CurrencyPair, on_delete=models.CASCADE, related_name="audit_logs")
    old_rate   = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    new_rate   = models.DecimalField(max_digits=20, decimal_places=6)
    source     = models.CharField(max_length=10, choices=ExchangeRate.SOURCE_CHOICES, default="manual")
    action     = models.CharField(max_length=10, choices=ACTION_CHOICES, default="updated")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    note       = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'api'   
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.pair} {self.action}: {self.old_rate} → {self.new_rate} by {self.changed_by} @ {self.created_at:%Y-%m-%d %H:%M}"