import random
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from api.models import CurrencyPair, ExchangeRate


def _quant6(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Seed Sprint 2 rate history: 30 daily ExchangeRate rows per CurrencyPair (90 pairs)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Number of daily points per pair (default 30)")
        parser.add_argument("--source", type=str, default="seed", help="Rate source label (default seed)")

    def handle(self, *args, **options):
        days = int(options["days"])
        source = options["source"]

        pairs = CurrencyPair.objects.select_related("base_currency", "quote_currency").all()
        if not pairs.exists():
            raise CommandError("No CurrencyPair found. Run: python manage.py seed_sprint1 first.")

        now = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)

        created = 0
        updated = 0

        for pair in pairs:
            # deterministic RNG seed per pair so teammates get the same dataset
            seed_value = abs(hash(pair.code)) % (2**32)
            rng = random.Random(seed_value)

            # base rate between ~0.5 and ~2.0 (kept stable and positive)
            base_rate = Decimal(str(rng.uniform(0.5, 2.0)))

            # simple random-walk history around base_rate
            current = base_rate
            for i in range(days):
                as_of = now - timedelta(days=(days - 1 - i))  # oldest -> newest

                # daily drift within +-2%
                drift = Decimal(str(rng.uniform(-0.02, 0.02)))
                current = current * (Decimal("1") + drift)

                # clamp to avoid extreme values
                if current < Decimal("0.05"):
                    current = Decimal("0.05")
                if current > Decimal("10"):
                    current = Decimal("10")

                rate_val = _quant6(current)

                obj, is_created = ExchangeRate.objects.update_or_create(
                    pair=pair,
                    as_of=as_of,
                    defaults={"rate": rate_val, "source": source},
                )
                created += int(is_created)
                updated += int(not is_created)

        self.stdout.write(self.style.SUCCESS(
            f"Sprint2 rate history seeded. pairs={pairs.count()}, days={days}, created={created}, updated={updated}, total_rates={ExchangeRate.objects.count()}"
        ))