from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.models import UserProfile, APIHealthStatus

User = get_user_model()


class Command(BaseCommand):
    help = "Seed Sprint 3 admin user, role profiles, and API health status rows."

    def handle(self, *args, **options):
        admin_user, created = User.objects.get_or_create(
            username="admin_fx",
            defaults={
                "email": "admin_fx@example.com",
                "is_staff": True,
                "is_superuser": True,
            }
        )

        if created:
            admin_user.set_password("AdminPass123!")
            admin_user.save()
        else:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()

        UserProfile.objects.update_or_create(
            user=admin_user,
            defaults={"role": UserProfile.Role.ADMIN}
        )

        demo_user = User.objects.filter(username="demo_customer").first()
        if demo_user:
            UserProfile.objects.update_or_create(
                user=demo_user,
                defaults={"role": UserProfile.Role.CUSTOMER}
            )

        providers = [
            {
                "provider_name": "ExchangeRateAPI",
                "endpoint": "https://api.exchangerate.host/latest",
            },
            {
                "provider_name": "ManualEntry",
                "endpoint": "",
            },
            {
                "provider_name": "CSVImport",
                "endpoint": "",
            },
        ]

        for p in providers:
            APIHealthStatus.objects.update_or_create(
                provider_name=p["provider_name"],
                defaults={
                    "endpoint": p["endpoint"],
                    "status": APIHealthStatus.Status.UNKNOWN,
                    "status_code": None,
                    "response_time_ms": None,
                    "message": "",
                    "checked_at": None,
                }
            )

        self.stdout.write(self.style.SUCCESS(
            "Sprint3 seed complete: admin user, role profiles, and API health status initialized."
        ))