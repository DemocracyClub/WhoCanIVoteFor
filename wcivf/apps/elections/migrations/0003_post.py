# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-24 11:51
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elections", "0002_auto_20160323_1533")]

    operations = [
        migrations.CreateModel(
            name="Post",
            fields=[
                (
                    "ynr_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("label", models.CharField(blank=True, max_length=255)),
                ("role", models.CharField(blank=True, max_length=255)),
                ("group", models.CharField(blank=True, max_length=100)),
                ("organization", models.CharField(blank=True, max_length=100)),
                ("area_name", models.CharField(blank=True, max_length=100)),
                ("area_id", models.CharField(blank=True, max_length=100)),
                (
                    "election",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="elections.Election",
                    ),
                ),
            ],
        )
    ]
