from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Currency, CurrencyPair, PortfolioHolding


CURRENCIES = [
    {"code": "GBP", "name": "British Pound",      "symbol": "£",    "flag": "🇬🇧"},
    {"code": "USD", "name": "US Dollar",           "symbol": "$",    "flag": "🇺🇸"},
    {"code": "EUR", "name": "Euro",                "symbol": "€",    "flag": "🇪🇺"},
    {"code": "JPY", "name": "Japanese Yen",        "symbol": "¥",    "flag": "🇯🇵"},
    {"code": "CNY", "name": "Chinese Yuan",        "symbol": "¥",    "flag": "🇨🇳"},
    {"code": "HKD", "name": "Hong Kong Dollar",    "symbol": "HK$",  "flag": "🇭🇰"},
    {"code": "AUD", "name": "Australian Dollar",   "symbol": "A$",   "flag": "🇦🇺"},
    {"code": "CAD", "name": "Canadian Dollar",     "symbol": "C$",   "flag": "🇨🇦"},
    {"code": "CHF", "name": "Swiss Franc",         "symbol": "CHF",  "flag": "🇨🇭"},
    {"code": "SGD", "name": "Singapore Dollar",    "symbol": "S$",   "flag": "🇸🇬"},
]

# Base = GBP, quote = other currency, rate = how many quote per 1 GBP
PAIRS = [
    ("GBP", "USD", "1.270000",  "0.45"),
    ("GBP", "EUR", "1.170000",  "-0.12"),
    ("GBP", "JPY", "191.50000", "0.80"),
    ("GBP", "CNY", "9.210000",  "0.22"),
    ("GBP", "HKD", "9.920000",  "0.15"),
    ("GBP", "AUD", "1.970000",  "-0.30"),
    ("GBP", "CAD", "1.730000",  "0.10"),
    ("GBP", "CHF", "1.130000",  "-0.05"),
    ("GBP", "SGD", "1.700000",  "0.20"),
]


class Command(BaseCommand):
    help = "Seed the database with currencies, pairs, and a demo user with holdings"

    def handle(self, *args, **kwargs):
        # Currencies
        for c in CURRENCIES:
            Currency.objects.get_or_create(code=c["code"], defaults={
                "name": c["name"], "symbol": c["symbol"], "flag": c["flag"], "enabled": True
            })
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(CURRENCIES)} currencies"))

        # Pairs
        for base_code, quote_code, rate, change_pct in PAIRS:
            base = Currency.objects.get(code=base_code)
            quote = Currency.objects.get(code=quote_code)
            CurrencyPair.objects.update_or_create(
                base=base, quote=quote,
                defaults={"rate": rate, "change_pct": change_pct, "enabled": True}
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(PAIRS)} currency pairs"))

        #Testing customer user
        demo_user, created = User.objects.get_or_create(username="demo")
        if created:
            demo_user.set_password("demo1234")
            demo_user.save()
            self.stdout.write(self.style.SUCCESS("Created demo user (demo / demo1234)"))

        # Tsting holdings
        demo_holdings = [
            ("GBP", "1500.000000", "1.000000"),
            ("USD", "800.000000",  "1.265000"),
            ("EUR", "500.000000",  "1.155000"),
            ("JPY", "50000.000000","190.000000"),
        ]
        for code, amount, avg_rate in demo_holdings:
            currency = Currency.objects.get(code=code)
            PortfolioHolding.objects.get_or_create(
                user=demo_user, currency=currency,
                defaults={"amount": amount, "avg_buy_rate": avg_rate}
            )
        self.stdout.write(self.style.SUCCESS("Seeded demo portfolio holdings"))
        self.stdout.write(self.style.SUCCESS("Done! Run: python manage.py seed_data"))
