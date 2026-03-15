# from django.contrib import admin
# from .models import (
#     Currency,
#     CurrencyPair,
#     PortfolioHolding,
#     ExchangeRate,
#     Trade,
#     LimitOrder,
#     RateAuditLog,
#     APIHealthStatus,
#     UserProfile,
# )

# @admin.register(Currency)
# class CurrencyAdmin(admin.ModelAdmin):
#     list_display = ("flag", "code", "name", "symbol", "is_enabled", "updated_at")
#     list_filter = ("is_enabled",)
#     search_fields = ("code", "name")
#     ordering = ("code",)


# @admin.register(CurrencyPair)
# class CurrencyPairAdmin(admin.ModelAdmin):
#     list_display = ("base_currency", "quote_currency", "is_enabled", "updated_at")
#     list_filter = ("is_enabled", "base_currency", "quote_currency")
#     search_fields = ("base_currency__code", "quote_currency__code")
#     ordering = ("base_currency__code", "quote_currency__code")


# @admin.register(PortfolioHolding)
# class PortfolioHoldingAdmin(admin.ModelAdmin):
#     list_display = ("user", "currency", "amount", "updated_at")
#     list_filter = ("currency",)
#     search_fields = ("user__username", "currency__code")
#     ordering = ("user__username", "currency__code")

# @admin.register(ExchangeRate)
# class ExchangeRateAdmin(admin.ModelAdmin):
#     list_display = ("pair", "rate", "as_of", "source")
#     list_filter = ("source", "pair")
#     search_fields = ("pair__base_currency__code", "pair__quote_currency__code")
#     ordering = ("-as_of",)


# @admin.register(Trade)
# class TradeAdmin(admin.ModelAdmin):
#     list_display = ("user", "pair", "side", "amount_base", "rate", "amount_quote", "status", "executed_at")
#     list_filter = ("status", "side", "pair")
#     search_fields = ("user__username", "pair__base_currency__code", "pair__quote_currency__code")
#     ordering = ("-executed_at",)


# @admin.register(LimitOrder)
# class LimitOrderAdmin(admin.ModelAdmin):
#     list_display = ("user", "pair", "side", "amount_base", "limit_rate", "status", "created_at", "executed_at")
#     list_filter = ("status", "side", "pair")
#     search_fields = ("user__username", "pair__base_currency__code", "pair__quote_currency__code")
#     ordering = ("-created_at",)

# @admin.register(RateAuditLog)
# class RateAuditLogAdmin(admin.ModelAdmin):
#     list_display = ("pair", "rate", "source", "action", "changed_by", "created_at")
#     list_filter = ("source", "action")
#     search_fields = ("pair__base_currency__code", "pair__quote_currency__code", "changed_by__username")
#     ordering = ("-created_at",)


# @admin.register(APIHealthStatus)
# class APIHealthStatusAdmin(admin.ModelAdmin):
#     list_display = ("provider_name", "status", "status_code", "response_time_ms", "checked_at", "updated_at")
#     list_filter = ("status",)
#     search_fields = ("provider_name",)
#     ordering = ("provider_name",)


# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ("user", "role", "created_at")
#     list_filter = ("role",)
#     search_fields = ("user__username", "user__email")
#     ordering = ("user__username",)
