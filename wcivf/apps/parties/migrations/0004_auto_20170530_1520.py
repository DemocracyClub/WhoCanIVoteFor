# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-05-30 15:20
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("elections", "0016_postelection_contested"),
        ("parties", "0003_auto_20160422_1148"),
    ]

    operations = [
        migrations.CreateModel(
            name="Manifesto",
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
                    "country",
                    models.CharField(
                        choices=[
                            ("United Kingdom", "United Kingdom"),
                            ("England", "England"),
                            ("Scotland", "Scotland"),
                            ("Wales", "Wales"),
                            ("Northern Ireland", "Northern Ireland"),
                        ],
                        default="UK",
                        max_length=200,
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[("English", "English"), ("Welsh", "Welsh")],
                        default="English",
                        max_length=200,
                    ),
                ),
                ("pdf_url", models.URLField(blank=True)),
                ("web_url", models.URLField(blank=True)),
                (
                    "election",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="elections.Election",
                    ),
                ),
                (
                    "party",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="parties.Party",
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="manifesto",
            unique_together={("party", "election", "country", "language")},
        ),
    ]
