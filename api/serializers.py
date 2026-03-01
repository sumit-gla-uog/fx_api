from rest_framework import serializers
from .models import Currency, CurrencyPair, PortfolioHolding


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "flag", "code", "name", "symbol", "is_enabled"]


class CurrencyPairSerializer(serializers.ModelSerializer):
    base = serializers.CharField(source="base_currency.code", read_only=True)
    quote = serializers.CharField(source="quote_currency.code", read_only=True)
    code = serializers.CharField(read_only=True)

    class Meta:
        model = CurrencyPair
        fields = ["id", "base", "quote", "code", "is_enabled"]


class PortfolioHoldingSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(source="currency.code", read_only=True)

    class Meta:
        model = PortfolioHolding
        fields = ["id", "currency", "amount"]
