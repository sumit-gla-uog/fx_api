from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("api", "0003_alter_pricehistory_recorded_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="RateAuditLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "old_rate",
                    models.DecimalField(
                        blank=True, decimal_places=6, max_digits=20, null=True
                    ),
                ),
                ("new_rate", models.DecimalField(decimal_places=6, max_digits=20)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("api", "API"),
                            ("manual", "Manual"),
                            ("csv", "CSV Import"),
                        ],
                        default="manual",
                        max_length=10,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("updated", "Updated"),
                            ("csv", "CSV Import"),
                        ],
                        default="updated",
                        max_length=10,
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "pair",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_logs",
                        to="api.currencypair",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ExchangeRate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("rate", models.DecimalField(decimal_places=6, max_digits=20)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("api", "API"),
                            ("manual", "Manual"),
                            ("csv", "CSV Import"),
                        ],
                        default="api",
                        max_length=10,
                    ),
                ),
                ("as_of", models.DateTimeField(auto_now_add=True)),
                (
                    "pair",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exchange_rates",
                        to="api.currencypair",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="rate_updates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-as_of"],
            },
        ),
    ]
