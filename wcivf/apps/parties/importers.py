import sys
from collections import namedtuple

from core.mixins import ReadFromUrlMixin, ReadFromFileMixin
from core.helpers import twitter_username
from elections.models import PostElection, Election
from parties.models import LocalParty, Party


LocalElection = namedtuple("LocalElection", ["date", "csv_files"])


class LocalPartyImporter(ReadFromUrlMixin, ReadFromFileMixin):

    # TODO check if this need updating
    JOINT_PARTIES = [["party:53", "joint-party:53-119"]]

    def __init__(self, election, force_update=False, from_file=False):
        self.election = election
        self.force_update = force_update
        self.read_from = getattr(self, "read_from_url")
        if from_file:
            self.read_from = getattr(self, "read_from_file")

    def write(self, msg):
        """
        Ensures all outputs include a new line
        """
        sys.stdout.write(f"{msg}\n")

    def delete_parties_for_election_date(self):
        """
        Deletes LocalParty objects associated with elections for the given
        election date
        """
        count, _ = LocalParty.objects.filter(
            post_election__election__election_date=self.election.date,
        ).delete()
        self.write(f"Deleted {count} local parties for {self.election.date}")

    def current_elections(self):
        """
        Checks for current Election objects with the given date
        """
        if self.force_update:
            return True

        return Election.objects.filter(
            current=True, election_date=self.election.date
        ).exists()

    def get_party_list_from_party_id(self, party_id):
        """
        Checks for any joint parties for the given party id
        """
        party_id = f"party:{party_id}"

        for party_list in self.JOINT_PARTIES:
            if party_id in party_list:
                return party_list
        return [party_id]

    def get_parties(self, party_id):
        """
        Return a QuerySet of Party objects for the party_id
        """
        party_list = self.get_party_list_from_party_id(party_id)
        return Party.objects.filter(party_id__in=party_list)

    def get_ballots(self, election_id, parties):
        """
        Attempts to find a single PostElection object for the election_id. If
        this does not exist, it may be that the ID is for an Election object, so
        we return all ballots for that election ID.
        """
        ballots = PostElection.objects.filter(ballot_paper_id=election_id)

        if not ballots:
            # This might be an election ID, in that case,
            # apply thie row to all post elections without
            # info already
            ballots = PostElection.objects.filter(
                election__slug=election_id
            ).exclude(localparty__parent__in=parties)

        return ballots

    def all_rows(self):
        """
        Yields all CSV rows from multiple files
        """
        for file in self.election.csv_files:
            yield from self.read_from(file)

    def add_local_party(self, row, party, ballots):
        """
        Takes a row of data, a Party, and a QuerySet of at least one
        PostElection objects, and craetes a LocalParty for each of the ballots.
        """
        twitter = twitter_username(url=row["Twitter"] or "")
        for post_election in ballots:
            local_party, created = LocalParty.objects.update_or_create(
                parent=party,
                post_election=post_election,
                defaults={
                    "name": self.get_name(row=row),
                    "twitter": twitter,
                    "facebook_page": row["Facebook"],
                    "homepage": row["Website"],
                    "email": row["Email"],
                },
            )

            self.write(
                f"{local_party.name} was {'created' if created else 'updated'}"
            )

    def get_name(self, row):
        """
        The sheet for Scottish/Welsh/GLA uses "Party Name" header so check for
        both
        """
        return row.get("Local party name", row.get("Party name"))

    def import_parties(self):
        """
        This is the main action that is run by the class. First existing
        LocalParty objects for an election are deleted. Then it validates the
        row contains data we can use. Then adds a LocalParty object for each
        parent party.
        """
        self.delete_parties_for_election_date()

        if not self.current_elections():
            self.write(
                f"No current elections for {self.election.date}, skipping"
            )
            return

        for row in self.all_rows():
            name = self.get_name(row=row)
            party_id = (row["party_id"] or "").strip()
            if not party_id or not name:
                self.write("Missing data, skipping row")
                continue

            parties = self.get_parties(party_id=party_id)
            if not parties:
                self.write(f"Parent party not found with IDs {party_id}")
                continue

            ballots = self.get_ballots(
                election_id=row["election_id"],
                parties=parties,
            )
            if not ballots:
                self.write("Skipping as no ballots to use")
                continue

            for party in parties:
                self.add_local_party(row, party, ballots)
