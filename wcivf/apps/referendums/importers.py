import sys

from core.mixins import ReadFromUrlMixin
from elections.models import PostElection
from referendums.models import Referendum


class ReferendumImporter(ReadFromUrlMixin):
    def __init__(self, url):
        self.url = url

    def get_ballots(self, election_id):
        """
        Returns a queryset of PostElection objects. Initially attempts to match
        a ballot_paper_id, if none found checks against Election.slug.
        """
        ballots = PostElection.objects.filter(ballot_paper_id=election_id)
        if ballots:
            return ballots

        return PostElection.objects.filter(election__slug=election_id)

    def create_referendum(self, data):
        """
        Create a Referendum object for the data and add M2M relationship.
        If there is no question we skip the row.
        If we cant find a matching ballot we skip the row.
        """
        if not data["question"]:
            return sys.stdout.write("No question to use, skipping\n")

        ballots = self.get_ballots(election_id=data.pop("election_id"))
        if not ballots:
            return sys.stdout.write("No ballots so skipping referendum\n")

        referendum = Referendum.objects.create(**data)
        referendum.ballots.set(ballots)
        sys.stdout.write(f"Created Referendum {referendum.pk}\n")
        return referendum

    def import_referendums(self):
        """
        Deletes existing referendum objects to ensure we have latest data and
        then creates a Referendum for each row
        """
        Referendum.objects.all().delete()
        for row in self.read_from_url(url=self.url):
            self.create_referendum(data=row)
