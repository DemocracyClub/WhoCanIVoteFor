# Generated by Django 4.1.6 on 2023-04-17 13:38

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("parties", "0016_partydescription"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartyEmblem",
            fields=[
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
                (
                    "ec_emblem_id",
                    models.PositiveIntegerField(
                        primary_key=True, serialize=False
                    ),
                ),
                ("emblem_url", models.TextField(null=True)),
                ("description", models.CharField(max_length=255)),
                ("date_approved", models.DateField(null=True)),
                ("default", models.BooleanField(default=False)),
                (
                    "party",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="emblems",
                        to="parties.party",
                    ),
                ),
            ],
            options={
                "ordering": ("-default", "ec_emblem_id"),
            },
        ),
    ]
