# Generated by Django 2.2.18 on 2021-02-25 11:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("feedback", "0002_feedback_token"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="feedback",
            options={"get_latest_by": "modified"},
        ),
    ]
