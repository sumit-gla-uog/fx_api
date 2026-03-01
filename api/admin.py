from django.contrib import admin
from .models import Currency, CurrencyPair, PortfolioHolding


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
