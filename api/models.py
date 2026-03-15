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
    

class PriceHistory(models.Model):
    """Snapshot of a pair's rate at a point in time."""

    pair = models.ForeignKey(CurrencyPair, on_delete=models.CASCADE, related_name='history')
    rate = models.DecimalField(max_digits=20, decimal_places=6)
    # recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_at = models.DateTimeField()

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.pair} @ {self.rate} ({self.recorded_at})"


class Trade(models.Model):
    """A completed market trade executed immediately at the current rate."""

    SIDE_CHOICES = [('buy', 'Buy'), ('sell', 'Sell')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trades')
    pair = models.ForeignKey(CurrencyPair, on_delete=models.CASCADE, related_name='trades')
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)          # 'buy' | 'sell'
    amount = models.DecimalField(max_digits=20, decimal_places=6)        # base currency amount
    rate = models.DecimalField(max_digits=20, decimal_places=6)          # rate at execution
    total = models.DecimalField(max_digits=20, decimal_places=6)         # amount * rate (quote)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-executed_at']

    def __str__(self):
        return f"{self.user.username} {self.side} {self.amount} {self.pair} @ {self.rate}"


class Order(models.Model):
    """A limit order that waits until the market hits the target rate."""
    SIDE_CHOICES = [('buy', 'Buy'), ('sell', 'Sell')]
    STATUS_CHOICES = [
        ('open',      'Open'),
        ('filled',    'Filled'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    pair = models.ForeignKey(CurrencyPair, on_delete=models.CASCADE, related_name='orders')
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    amount = models.DecimalField(max_digits=20, decimal_places=6)        # base currency amount
    limit_rate = models.DecimalField(max_digits=20, decimal_places=6)    # target rate
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} {self.side} {self.amount} {self.pair} limit@{self.limit_rate} [{self.status}]"
