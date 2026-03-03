from django.db import models
from django.contrib.auth.models import User


class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    flag = models.CharField(max_length=10, blank=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class CurrencyPair(models.Model):
    base = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='base_pairs')
    quote = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='quote_pairs')
    rate = models.DecimalField(max_digits=20, decimal_places=6)
    change_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)  # % change 24h
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ('base', 'quote')

    def __str__(self):
        return f"{self.base.code}/{self.quote.code}"


class PortfolioHolding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='holdings')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=6)
    avg_buy_rate = models.DecimalField(max_digits=20, decimal_places=6, default=1)

    class Meta:
        unique_together = ('user', 'currency')

    def __str__(self):
        return f"{self.user.username} - {self.currency.code}"
