# Generated by Django 4.2.10 on 2024-03-27 18:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0047_person_statement_to_voters_last_updated"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="blue_sky_url",
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name="person",
            name="other_url",
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name="person",
            name="threads_url",
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name="person",
            name="tiktok_url",
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
    ]
