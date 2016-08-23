# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-23 14:12
from __future__ import unicode_literals

import django.contrib.postgres.fields.hstore
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='LoggedAction',
            fields=[
                ('event_id', models.IntegerField(primary_key=True, serialize=False)),
                ('table_name', models.TextField()),
                ('user_name', models.TextField(null=True)),
                ('created_at', models.DateTimeField()),
                ('action', models.CharField(choices=[('I', 'INSERT'), ('U', 'UPDATE'), ('D', 'DELETE'), ('T', 'TRUNCATE')], max_length=1)),
                ('row_data', django.contrib.postgres.fields.hstore.HStoreField(null=True)),
                ('changed_fields', django.contrib.postgres.fields.hstore.HStoreField(null=True)),
            ],
            options={
                'verbose_name': 'logged action',
                'db_table': 'audit_logged_actions',
                'verbose_name_plural': 'logged actions',
                'ordering': ('created_at',),
                'managed': False,
            },
        ),
    ]
