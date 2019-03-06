# Generated by Django 2.1.7 on 2019-03-06 19:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("projects", "0002_auto_20190304_2247")]

    operations = [
        migrations.AlterModelOptions(
            name="cost",
            options={
                "ordering": ["pk"],
                "verbose_name": "cost",
                "verbose_name_plural": "costs",
            },
        ),
        migrations.AlterModelOptions(
            name="effort",
            options={
                "ordering": ["pk"],
                "verbose_name": "effort",
                "verbose_name_plural": "efforts",
            },
        ),
        migrations.RemoveField(model_name="cost", name="position"),
        migrations.AlterUniqueTogether(name="effort", unique_together=set()),
    ]
