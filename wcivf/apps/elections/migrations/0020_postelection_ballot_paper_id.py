# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-17 16:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elections", "0019_election_metadata")]

    operations = [
        migrations.AddField(
            model_name="postelection",
            name="ballot_paper_id",
            field=models.CharField(blank=True, max_length=800),
        )
    ]
