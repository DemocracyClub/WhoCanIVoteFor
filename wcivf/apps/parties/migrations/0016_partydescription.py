# Generated by Django 4.1.6 on 2023-04-17 11:16

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "parties",
            "0015_party_date_deregistered_party_date_registered_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="PartyDescription",
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
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                ("description", models.CharField(max_length=800)),
                ("date_description_approved", models.DateField(null=True)),
                (
                    "party",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="party_descriptions",
                        to="parties.party",
                    ),
                ),
            ],
            options={
                "unique_together": {("party", "description")},
            },
        ),
    ]
