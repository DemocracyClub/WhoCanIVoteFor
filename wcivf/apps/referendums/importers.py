import sys

from core.mixins import ImportAdditionalElectionMixin
from referendums.models import Referendum


class ReferendumImporter(ImportAdditionalElectionMixin):
    model = Referendum

    def create_object(self, row):
        """
        Create a Referendum object for the data and add M2M relationship.
        If there is no question we skip the row.
        If we cant find a matching ballot we skip the row.
        """
        if not row["question"]:
            return sys.stdout.write("No question to use, skipping\n")

        ballots = self.get_ballots(election_id=row.pop("election_id"))
        if not ballots:
            return sys.stdout.write("No ballots so skipping referendum\n")

        referendum = Referendum.objects.create(**row)
        referendum.ballot_dict.set(ballots)
        sys.stdout.write(f"Created Referendum {referendum.pk}\n")
        return referendum
