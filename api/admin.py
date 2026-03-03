from django.contrib import admin
from .models import Currency, CurrencyPair, PortfolioHolding, ExchangeRate, Trade, LimitOrder

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("flag", "code", "name", "symbol", "is_enabled", "updated_at")
    list_filter = ("is_enabled",)
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(CurrencyPair)
class CurrencyPairAdmin(admin.ModelAdmin):
    list_display = ("base_currency", "quote_currency", "is_enabled", "updated_at")
    list_filter = ("is_enabled", "base_currency", "quote_currency")
    search_fields = ("base_currency__code", "quote_currency__code")
    ordering = ("base_currency__code", "quote_currency__code")


@admin.register(PortfolioHolding)
class PortfolioHoldingAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "amount", "updated_at")
    list_filter = ("currency",)
    search_fields = ("user__username", "currency__code")
    ordering = ("user__username", "currency__code")

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("pair", "rate", "as_of", "source")
    list_filter = ("source", "pair")
    search_fields = ("pair__base_currency__code", "pair__quote_currency__code")
    ordering = ("-as_of",)


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("user", "pair", "side", "amount_base", "rate", "amount_quote", "status", "executed_at")
    list_filter = ("status", "side", "pair")
    search_fields = ("user__username", "pair__base_currency__code", "pair__quote_currency__code")
    ordering = ("-executed_at",)


@admin.register(LimitOrder)
class LimitOrderAdmin(admin.ModelAdmin):
    list_display = ("user", "pair", "side", "amount_base", "limit_rate", "status", "created_at", "executed_at")
    list_filter = ("status", "side", "pair")
    search_fields = ("user__username", "pair__base_currency__code", "pair__quote_currency__code")
    ordering = ("-created_at",)
