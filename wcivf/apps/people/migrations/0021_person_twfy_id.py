# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-06-02 15:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("people", "0020_person_favourite_biscuit")]

    operations = [
        migrations.AddField(
            model_name="person",
            name="twfy_id",
            field=models.IntegerField(blank=True, null=True),
        )
    ]
