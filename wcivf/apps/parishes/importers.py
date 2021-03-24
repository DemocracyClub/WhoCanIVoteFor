import sys
from core.mixins import ImportAdditionalElectionMixin

from parishes.models import ParishCouncilElection


class ParishCouncilElectionImporter(ImportAdditionalElectionMixin):
    model = ParishCouncilElection

    def is_contested(self, value):
        yes = ["y", "yes"]
        value = str(value).strip().lower()
        return value in yes

    def num_ward_seats(self, value):
        try:
            return int(value)
        except ValueError:
            return 0

    def create_object(self, row):
        election_id = row.pop("Election ID")
        if not election_id:
            return sys.stdout.write.write("No election id, skipping row\n")

        ballots = self.get_ballots(election_id=election_id)
        if not ballots:
            return sys.stdout.write("No ballots for ID, skipping row\n")

        parish = ParishCouncilElection.objects.create(
            council_name=row["Council Name"],
            council_type=row["Council Type"],
            local_authority=row["Local Authority"],
            parish_ward_name=row["Parish Ward Name"],
            ward_seats=self.num_ward_seats(row["Ward Seats"]),
            website=row["Council Website"],
            precept=row["Precept 2020-2021"],
            sopn=row["Link to SoPN PDF"],
            is_contested=self.is_contested(row["Contested (Y/N)?"]),
        )
        parish.ballots.set(ballots)
        sys.stdout.write(f"Created ParishCouncilElection <{parish.pk}>\n")
        return parish
