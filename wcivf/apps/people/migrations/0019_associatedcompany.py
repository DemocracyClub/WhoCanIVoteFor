# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-05-19 08:45
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("people", "0018_auto_20170518_1255")]

    operations = [
        migrations.CreateModel(
            name="AssociatedCompany",
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
                ("company_name", models.CharField(max_length=255)),
                ("company_number", models.CharField(max_length=50)),
                ("company_status", models.CharField(max_length=50)),
                ("role", models.CharField(max_length=50)),
                (
                    "role_status",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                ("role_appointed_date", models.DateField()),
                ("role_resigned_date", models.DateField(blank=True, null=True)),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="people.Person",
                    ),
                ),
            ],
        )
    ]
