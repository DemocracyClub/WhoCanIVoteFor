from django.db import migrations
from uk_election_timetables.calendars import Country
from uk_election_timetables.election_ids import (
    InvalidElectionIdError,
    from_election_id,
)

country_map = {
    "ENG": Country.ENGLAND,
    "SCT": Country.SCOTLAND,
    "WLS": Country.WALES,
    "NIR": Country.NORTHERN_IRELAND,
}


def backfill_timetable_fields(apps, schema_editor):
    PostElection = apps.get_model("elections", "PostElection")

    qs = (
        PostElection.objects.using(schema_editor.connection.alias)
        # We don't have logic for computing timetable for
        # EU Parliament elections but some do exist in the DB
        # from back in the day
        .exclude(ballot_paper_id__startswith="europarl.")
        # There is no nominations or SOPN for referenda
        # Notice of election deadline is applicable
        # but not implemented
        .exclude(ballot_paper_id__startswith="ref.")
        .select_related("post")
    )

    ballots_to_update = []

    for ballot in qs.iterator():
        try:
            timetable = from_election_id(
                ballot.ballot_paper_id,
                country=country_map[ballot.post.territory],
            )
        except InvalidElectionIdError:
            # Some really old elections in WCIVF don't have a EE ballot ID
            continue

        ballot.notice_of_election_deadline = (
            timetable.notice_of_election_deadline
        )
        ballot.close_of_nominations = timetable.close_of_nominations
        ballot.sopn_publish_deadline = timetable.sopn_publish_deadline
        ballot.registration_deadline = timetable.registration_deadline
        ballot.postal_vote_application_deadline = (
            timetable.postal_vote_application_deadline
        )
        if ballot.requires_voter_id == "EA-2022":
            ballot.vac_application_deadline = timetable.vac_application_deadline
        ballots_to_update.append(ballot)

    batch_size = 2000
    for i in range(0, len(ballots_to_update), batch_size):
        qs.bulk_update(
            ballots_to_update[i : i + batch_size],
            [
                "notice_of_election_deadline",
                "close_of_nominations",
                "sopn_publish_deadline",
                "registration_deadline",
                "postal_vote_application_deadline",
                "vac_application_deadline",
            ],
        )


def clear_timetable_fields(apps, schema_editor):
    PostElection = apps.get_model("elections", "PostElection")
    PostElection.objects.using(schema_editor.connection.alias).update(
        notice_of_election_deadline=None,
        close_of_nominations=None,
        sopn_publish_deadline=None,
        registration_deadline=None,
        postal_vote_application_deadline=None,
        vac_application_deadline=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("elections", "0053_postelection_timetable_fields"),
    ]

    operations = [
        migrations.RunPython(backfill_timetable_fields, clear_timetable_fields)
    ]
