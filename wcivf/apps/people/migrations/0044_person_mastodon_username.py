# Generated by Django 4.2 on 2023-07-11 13:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0043_personpost_rank"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="mastodon_username",
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
    ]
