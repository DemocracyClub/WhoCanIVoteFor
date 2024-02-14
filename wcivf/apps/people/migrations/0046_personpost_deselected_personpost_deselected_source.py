# Generated by Django 4.2.6 on 2024-01-17 16:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0045_person_delisted"),
    ]

    operations = [
        migrations.AddField(
            model_name="personpost",
            name="deselected",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="personpost",
            name="deselected_source",
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
    ]
