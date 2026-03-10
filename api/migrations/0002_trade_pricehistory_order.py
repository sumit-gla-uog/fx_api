from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Trade",
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
                    "side",
                    models.CharField(
                        choices=[("buy", "Buy"), ("sell", "Sell")], max_length=4
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=6, max_digits=20)),
                ("rate", models.DecimalField(decimal_places=6, max_digits=20)),
                ("total", models.DecimalField(decimal_places=6, max_digits=20)),
                ("executed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "pair",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trades",
                        to="api.currencypair",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trades",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-executed_at"],
            },
        ),
        migrations.CreateModel(
            name="PriceHistory",
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
                ("recorded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "pair",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history",
                        to="api.currencypair",
                    ),
                ),
            ],
            options={
                "ordering": ["-recorded_at"],
            },
        ),
        migrations.CreateModel(
            name="Order",
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
                    "side",
                    models.CharField(
                        choices=[("buy", "Buy"), ("sell", "Sell")], max_length=4
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=6, max_digits=20)),
                ("limit_rate", models.DecimalField(decimal_places=6, max_digits=20)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("filled", "Filled"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="open",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "pair",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orders",
                        to="api.currencypair",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
