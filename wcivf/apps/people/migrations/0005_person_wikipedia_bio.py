# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-14 12:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("people", "0004_auto_20160414_0927")]

    operations = [
        migrations.AddField(
            model_name="person",
            name="wikipedia_bio",
            field=models.TextField(null=True),
        )
    ]
