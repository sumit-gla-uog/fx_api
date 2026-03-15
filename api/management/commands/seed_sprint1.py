from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Currency, CurrencyPair, PortfolioHolding

# 10 currencies as per the wireframes / design
DEFAULT_CURRENCIES = [
    {"flag": "GB", "code": "GBP", "name": "British Pound", "symbol": "£"},
    {"flag": "US", "code": "USD", "name": "US Dollar", "symbol": "$"},
    {"flag": "EU", "code": "EUR", "name": "Euro", "symbol": "€"},
    {"flag": "JP", "code": "JPY", "name": "Japanese Yen", "symbol": "¥"},
    {"flag": "CN", "code": "CNY", "name": "Chinese Yuan", "symbol": "¥"},
    {"flag": "HK", "code": "HKD", "name": "Hong Kong Dollar", "symbol": "HK$"},
    {"flag": "AU", "code": "AUD", "name": "Australian Dollar", "symbol": "A$"},
    {"flag": "CA", "code": "CAD", "name": "Canadian Dollar", "symbol": "C$"},
    {"flag": "CH", "code": "CHF", "name": "Swiss Franc", "symbol": "CHF"},
    {"flag": "SG", "code": "SGD", "name": "Singapore Dollar", "symbol": "S$"},
]

# Demo holdings aligned with the portfolio wireframe (example only)
DEFAULT_DEMO_HOLDINGS = [
    ("GBP", Decimal("9900.00")),
    ("USD", Decimal("5061.26")),
    ("EUR", Decimal("3000.00")),
    ("JPY", Decimal("500000.00")),
    ("CNY", Decimal("20000.00")),
    ("HKD", Decimal("15000.00")),
]

class Command(BaseCommand):
    help = "Seed Sprint 1 database tables: currencies, currency pairs, demo portfolio holdings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="demo_customer",
            help="Username for the demo customer user (default: demo_customer).",
        )
        parser.add_argument(
            "--password",
            default="DemoPass123!",
            help="Password for the demo customer user (default: DemoPass123!).",
        )
        parser.add_argument(
            "--email",
            default="demo@example.com",
            help="Email for the demo customer user (default: demo@example.com).",
        )
        parser.add_argument(
            "--no-user",
            action="store_true",
            help="Do not create/update demo user and holdings (seed only currencies and pairs).",
        )
        parser.add_argument(
            "--pairs-mode",
            choices=["all"],
            default="all",
            help="Currency pair seeding strategy. Currently supports: all (all ordered pairs among the 10 currencies).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # 1) Currencies
        c_created = 0
        c_updated = 0
        code2obj = {}
        for c in DEFAULT_CURRENCIES:
            obj, created = Currency.objects.update_or_create(
                code=c["code"],
                defaults={
                    "flag": c.get("flag",""),
                    "name": c["name"],
                    "symbol": c.get("symbol", ""),
                    "is_enabled": True,
                },
            )
            code2obj[obj.code] = obj
            c_created += int(created)
            c_updated += int(not created)

        # 2) Currency pairs (multi-base: allow any two different currencies)
        p_created = 0
        for base_code, base_obj in code2obj.items():
            for quote_code, quote_obj in code2obj.items():
                if base_code == quote_code:
                    continue
                _, created = CurrencyPair.objects.update_or_create(
                    base_currency=base_obj,
                    quote_currency=quote_obj,
                    defaults={"is_enabled": True},
                )
                p_created += int(created)

        # 3) Demo user + holdings
        u_created = 0
        h_created = 0
        h_updated = 0
        if not options["no_user"]:
            User = get_user_model()
            username = options["username"]
            password = options["password"]
            email = options["email"]

            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email},
            )
            u_created = int(created)

            # ensure password is set (idempotent)
            user.set_password(password)
            if email and user.email != email:
                user.email = email
            user.save()

            for code, amt in DEFAULT_DEMO_HOLDINGS:
                cur = code2obj.get(code)
                if not cur:
                    continue
                holding, created = PortfolioHolding.objects.update_or_create(
                    user=user,
                    currency=cur,
                    defaults={"amount": amt},
                )
                h_created += int(created)
                h_updated += int(not created)

        self.stdout.write(self.style.SUCCESS(
            "Sprint 1 seed complete: "
            f"currencies(created={c_created}, updated={c_updated}, total={Currency.objects.count()}); "
            f"pairs(created={p_created}, total={CurrencyPair.objects.count()}); "
            f"demo_user(created={u_created}); holdings(created={h_created}, updated={h_updated})."
        ))
