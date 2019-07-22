# Generated by Django 2.1.7 on 2019-03-04 21:39

from decimal import Decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Offer",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "subtotal",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="subtotal",
                    ),
                ),
                (
                    "discount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="discount",
                    ),
                ),
                (
                    "liable_to_vat",
                    models.BooleanField(
                        default=True,
                        help_text="For example invoices to foreign institutions are not liable to VAT.",
                        verbose_name="liable to VAT",
                    ),
                ),
                (
                    "tax_rate",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("7.7"),
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="tax rate",
                    ),
                ),
                (
                    "total",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="total",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="created at"
                    ),
                ),
                (
                    "offered_on",
                    models.DateField(blank=True, null=True, verbose_name="offered on"),
                ),
                (
                    "closed_on",
                    models.DateField(blank=True, null=True, verbose_name="closed on"),
                ),
                ("title", models.CharField(max_length=200, verbose_name="title")),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="description"),
                ),
                (
                    "status",
                    models.PositiveIntegerField(
                        choices=[
                            (10, "In preparation"),
                            (20, "Offered"),
                            (30, "Accepted"),
                            (40, "Rejected"),
                        ],
                        default=10,
                        verbose_name="status",
                    ),
                ),
                (
                    "postal_address",
                    models.TextField(blank=True, verbose_name="postal address"),
                ),
                ("_code", models.IntegerField(verbose_name="code")),
                (
                    "owned_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="responsible",
                    ),
                ),
            ],
            options={
                "verbose_name": "offer",
                "verbose_name_plural": "offers",
                "ordering": ("-offered_on", "-pk"),
            },
        )
    ]
