# Generated by Django 2.1.7 on 2019-03-10 10:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0006_auto_20190309_2143"),
        ("logbook", "0003_auto_20190304_2247"),
    ]

    operations = [
        migrations.RemoveField(model_name="loggedcost", name="invoice"),
        migrations.RemoveField(model_name="loggedhours", name="invoice"),
        migrations.AddField(
            model_name="loggedcost",
            name="invoice_service",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="invoices.Service",
                verbose_name="invoice service",
            ),
        ),
        migrations.AddField(
            model_name="loggedhours",
            name="invoice_service",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="invoices.Service",
                verbose_name="invoice service",
            ),
        ),
    ]
