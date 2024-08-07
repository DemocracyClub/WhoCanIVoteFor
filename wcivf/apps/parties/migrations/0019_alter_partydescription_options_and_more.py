# Generated by Django 4.1.6 on 2023-06-14 15:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("parties", "0018_alter_partydescription_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="partydescription",
            options={"ordering": ["-active", "date_description_approved"]},
        ),
        migrations.AlterModelOptions(
            name="partyemblem",
            options={"ordering": ("-default", "-active", "ec_emblem_id")},
        ),
        migrations.AddField(
            model_name="partydescription",
            name="active",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="partyemblem",
            name="active",
            field=models.BooleanField(default=False),
        ),
    ]
