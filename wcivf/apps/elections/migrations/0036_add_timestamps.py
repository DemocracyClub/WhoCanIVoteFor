# Generated by Django 3.2.7 on 2021-10-05 15:30

from django.db import migrations, models
import django.utils.timezone
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ("elections", "0035_auto_20210928_1303"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="postelection",
            options={"get_latest_by": "ynr_modified"},
        ),
        migrations.AddField(
            model_name="postelection",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="created",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="postelection",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(
                auto_now=True, verbose_name="modified"
            ),
        ),
        migrations.AddField(
            model_name="postelection",
            name="ynr_modified",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp of when this ballot was updated in the YNR",
                null=True,
            ),
        ),
    ]
