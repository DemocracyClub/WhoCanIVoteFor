# Generated by Django 2.2.18 on 2021-03-25 16:10

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("elections", "0033_auto_20210210_1422"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParishCouncilElection",
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
                ("council_name", models.CharField(max_length=255)),
                (
                    "parish_ward_name",
                    models.CharField(blank=True, max_length=255),
                ),
                ("local_authority", models.CharField(max_length=255)),
                ("council_type", models.CharField(max_length=255)),
                ("website", models.URLField(blank=True)),
                (
                    "precept",
                    models.CharField(
                        blank=True,
                        help_text="The amount of the parish councils share of the council tax",
                        max_length=255,
                    ),
                ),
                (
                    "sopn",
                    models.URLField(blank=True, help_text="Link to SoPN PDF"),
                ),
                ("ward_seats", models.PositiveIntegerField(default=0)),
                ("is_contested", models.NullBooleanField(default=None)),
                (
                    "ballots",
                    models.ManyToManyField(
                        related_name="parish_councils",
                        to="elections.PostElection",
                    ),
                ),
            ],
        ),
    ]
