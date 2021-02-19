import sys

from core.mixins import ReadFromUrlMixin
from core.helpers import twitter_username
from elections.models import PostElection
from parties.models import LocalParty, Party


class LocalPartyImporter(ReadFromUrlMixin):
    def __init__(self, url, stdout=sys.stdout) -> None:
        self.url = url
        self.stdout = stdout

    def get_party_list_from_party_id(self, party_id):
        party_id = f"party:{party_id}"

        PARTIES = [["party:53", "joint-party:53-119"]]

        for party_list in PARTIES:
            if party_id in party_list:
                return party_list
        return [party_id]

    def get_parties(self, party_id):
        party_list = self.get_party_list_from_party_id(party_id)
        return Party.objects.filter(party_id__in=party_list)

    def get_ballots(self, election_id, parties):
        ballots = PostElection.objects.filter(ballot_paper_id=election_id)

        if not ballots:
            # This might be an election ID, in that case,
            # apply thie row to all post elections without
            # info already
            ballots = PostElection.objects.filter(
                election__slug=election_id
            ).exclude(localparty__parent__in=parties)

        return ballots

    def add_parties(self):
        for row in self.read_from_url(url=self.url):
            name = row["Local party name"]
            party_id = (row["party_id"] or "").strip()
            if not party_id or not name:
                self.stdout.write("Missing data, skipping row\n")
                continue

            parties = self.get_parties(party_id=party_id)
            if not parties:
                self.stdout.write(
                    f"Parent party not found with IDs {party_id}\n"
                )
                continue

            ballots = self.get_ballots(
                election_id=row["election_id"],
                parties=parties,
            )
            if not ballots:
                self.stdout.write("Skipping as no ballots to use\n")
                continue

            for party in parties:
                self.add_local_party(row, party, ballots)

    def add_local_party(self, row, party, ballots):
        twitter = twitter_username(url=row["Twitter"] or "")
        for post_election in ballots:
            local_party, created = LocalParty.objects.update_or_create(
                parent=party,
                post_election=post_election,
                defaults={
                    "name": row["Local party name"],
                    "twitter": twitter,
                    "facebook_page": row["Facebook"],
                    "homepage": row["Website"],
                    "email": row["Email"],
                },
            )

            self.stdout.write(
                f"{local_party.name} was {'created' if created else 'updated'}\n"
            )
