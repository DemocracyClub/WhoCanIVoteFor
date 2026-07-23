from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("elections", "0053_postelection_timetable_fields"),
    ]

    operations = [
        migrations.RunPython(
            migrations.RunPython.noop, migrations.RunPython.noop
        )
    ]
