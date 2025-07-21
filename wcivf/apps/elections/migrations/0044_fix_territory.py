from django.db import migrations

post_map = {
    "E": "ENG",
    "W": "WLS",
    "N": "NIR",
    "S": "SCT",
}


def fix_territory(apps, schema_editor):
    Post = apps.get_model("elections", "Post")
    posts = Post.objects.using(schema_editor.connection.alias).exclude(
        territory__in=["ENG", "WLS", "NIR", "SCT"]
    )
    for post in posts:
        if not post.ynr_id.startswith("gss:"):
            raise ValueError(f"Can't infer territory for post {post.ynr_id}")
        post.territory = post_map[post.ynr_id[4]]
        post.save()


class Migration(migrations.Migration):
    dependencies = [
        ("elections", "0043_remove_election_ballot_papers_issued_and_more"),
    ]

    operations = [
        migrations.RunPython(
            code=fix_territory, reverse_code=migrations.RunPython.noop
        )
    ]
