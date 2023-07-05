import sys
from core.mixins import ImportAdditionalElectionMixin

from parishes.models import ParishCouncilElection


class ParishCouncilElectionImporter(ImportAdditionalElectionMixin):
    model = ParishCouncilElection

    def clean_is_contested(self, value):
        value = str(value).strip().lower()
        if value in ["y", "yes"]:
            return True
        if value in ["n", "no"]:
            return False
        return None

    def clean_num_ward_seats(self, value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def clean_precept(self, value):
        return value.strip("£ ")

    def create_object(self, row):
        # remove any whitespace
        row = {k: v.strip() for k, v in row.items()}
        election_id = row.pop("Election ID")
        if not election_id:
            return sys.stdout.write("No election id, skipping row\n")

        ballots = self.get_ballots(election_id=election_id)
        if not ballots:
            return sys.stdout.write(
                f"No ballots for election_id: '{election_id}', skipping row\n"
            )

        parish = ParishCouncilElection.objects.create(
            council_name=row["Council Name"],
            council_type=row["Council Type"],
            local_authority=row["Local Authority"],
            parish_ward_name=row["Parish Ward Name"],
            ward_seats=self.clean_num_ward_seats(row["Ward Seats"]),
            website=row["Council Website"],
            precept=self.clean_precept(row["Precept 2020-2021"]),
            sopn=row["Link to SoPN PDF"],
            is_contested=self.clean_is_contested(row["Contested (Y/N)?"]),
        )
        parish.ballot_dict.set(ballots)
        sys.stdout.write(f"Created ParishCouncilElection <{parish.pk}>\n")
        return parish
