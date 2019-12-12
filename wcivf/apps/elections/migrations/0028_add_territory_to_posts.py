from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("elections", "0027_unique_on_ballot_id")]

    operations = [
        migrations.AddField(
            model_name="post",
            name="territory",
            field=models.CharField(blank=True, max_length=3, serialize=True),
        )
    ]
