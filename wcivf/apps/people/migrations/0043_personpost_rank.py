# Generated by Django 4.1.6 on 2023-05-05 09:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("people", "0042_personpost_previous_party_affiliations"),
    ]

    operations = [
        migrations.AddField(
            model_name="personpost",
            name="rank",
            field=models.PositiveIntegerField(null=True),
        ),
    ]