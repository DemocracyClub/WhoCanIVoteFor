# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-22 11:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("parties", "0002_auto_20160412_1739")]

    operations = [
        migrations.AddField(
            model_name="party",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="party",
            name="wikipedia_url",
            field=models.URLField(blank=True),
        ),
    ]
