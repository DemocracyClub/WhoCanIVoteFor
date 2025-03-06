import sys
from collections import namedtuple

from core.helpers import twitter_username
from core.mixins import ReadFromFileMixin, ReadFromUrlMixin
from elections.models import Election, PostElection
from parties.models import LocalParty, Manifesto, NationalParty, Party

LocalElection = namedtuple("LocalElection", ["date", "csv_files"])
NationalElection = namedtuple("NationalElection", ["date", "csv_files"])


class LocalPartyImporter(ReadFromUrlMixin, ReadFromFileMixin):
    # TODO check if this need updating
    JOINT_PARTIES = [["party:53", "joint-party:53-119"]]

    def __init__(
        self,
        election,
        force_update=False,
        from_file=False,
    ):
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

    def delete_parties(self):
        """
        Deletes LocalParty objects associated with elections for the given
        election date
        """
        count, _ = LocalParty.objects.filter(
            file_url__in=self.election.csv_files,
        ).delete()

        self.write(f"Deleted {count} local parties")

    def delete_manifestos(self):
        count, _ = Manifesto.objects.filter(
            file_url__in=self.election.csv_files,
        ).delete()

        self.write(f"Deleted {count} manifestos")

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
        First checks if the election_id is a special case or is not a full
        election ID e.g. it is made of only two parts such as local.2022-05-05.
        In this case we return all ballots for the type of election and the
        date. Otherwise attempts to find a single PostElection object for the
        election_id. If this does not exist it may be that the ID is the slug
        of an Election object so we return all ballots related to the Election.
        """
        special_cases = ["senedd", "sp", "gla"]
        election_id_list = election_id.split(".")
        election_type = election_id_list[0]
        if len(election_id_list) == 2 or election_type in special_cases:
            ballots = PostElection.objects.filter(
                ballot_paper_id__startswith=f"{election_type}.",
                election__election_date=self.election.date,
            ).exclude(localparty__parent__in=parties)
        else:
            ballots = PostElection.objects.filter(ballot_paper_id=election_id)

        if not ballots:
            # This might be an election ID, in that case,
            # apply the row to all post elections without
            # info already
            ballots = PostElection.objects.filter(
                election__slug=election_id
            ).exclude(localparty__parent__in=parties)
        return ballots.filter(personpost__party__in=parties)

    def add_local_party(self, row, party, ballots, file_url):
        """
        Takes a row of data, a Party, and a QuerySet of at least one
        PostElection objects, and craetes a LocalParty for each of the ballots.
        """
        twitter = twitter_username(url=row["X"] or "")
        name = self.get_name(row=row)
        # only create local parties for ballots where a candidate is standing
        # for the parent party
        ballots = ballots.filter(personpost__party=party)
        for post_election in ballots.distinct():
            country = self.get_country(
                election_type=post_election.election.election_type
            )
            defaults = {
                "name": name,
                "twitter": twitter,
                "instagram": row.get("Instagram", "").strip(),
                "bluesky": row.get("Bluesky", "").strip(),
                "facebook_page": row["Facebook"],
                "homepage": row["Website"],
                "email": row["Email"],
                "is_local": country == "Local",
                "youtube_profile_url": row.get("Party broadcast", "").strip(),
                "contact_page_url": row.get("Contact page", "").strip(),
                "file_url": file_url,
            }

            _, created = LocalParty.objects.update_or_create(
                parent=party, post_election=post_election, defaults=defaults
            )
            msg = "Created" if created else "Updated"
            self.write(
                f"{msg} Local Party object for {party.party_name} in {post_election.ballot_paper_id}"
            )

        self.write(f"Imported Local Party objects for {name}")

    def get_name(self, row):
        """
        The sheet for Scottish/Welsh/GLA uses "Party Name" header so check for
        both
        """
        return row.get("Local party name", row.get("Party name"))

    def get_country(self, election_type):
        country_mapping = {
            "local": "Local",
            "senedd": "Wales",
            "sp": "Scotland",
        }
        return country_mapping.get(election_type, "UK")

    def import_parties(self):
        """
        This is the main action that is run by the class. First existing
        LocalParty objects for an election are deleted. Then it validates the
        row contains data we can use. Then adds a LocalParty object for each
        parent party.
        """
        self.delete_parties()
        self.delete_manifestos()
        if not self.current_elections():
            self.write(
                f"No current elections for {self.election.date}, skipping"
            )
            return

        for file_url in self.election.csv_files:
            rows = self.read_from(file_url)
            for row in rows:
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
                    election_id=row["election_id"].strip(), parties=parties
                )
                if not ballots:
                    self.write("Skipping as no ballots to use")
                    continue

                # store the PK's in a list as something strange is
                # happening later on - when trying to access
                # objects from the 'ballots' queryset after the
                # add_local_party method has been called, None is
                # returned instead of the object.
                # This resulted in the 'elections' queryset also
                # being empty. Storing the PK's in a list gets round
                # this but unclear why this is happening
                ballot_pks = list(ballots.values_list("pk", flat=True))
                elections = Election.objects.filter(
                    postelection__in=ballot_pks
                ).distinct()
                for party in parties:
                    self.add_local_party(row, party, ballots, file_url)
                    manifesto_web = row.get("Manifesto Website URL", "").strip()
                    manifesto_pdf = row.get("Manifesto PDF URL", "").strip()
                    if not any([manifesto_web, manifesto_pdf]):
                        self.write("No links to create Manifesto, skipping")
                        continue

                    for election in elections:
                        self.add_manifesto(row, party, election, file_url)

    def add_manifesto(self, row, party, election, file_url):
        manifesto_web = row.get("Manifesto Website URL", "").strip()
        manifesto_pdf = row.get("Manifesto PDF URL", "").strip()
        country = self.get_country(election_type="local")
        language = row.get("Manifesto Language", "English").strip()
        easy_read_url = row.get("Manifesto Easy Read PDF", "").strip()
        if any([manifesto_web, manifesto_pdf]):
            defaults = {
                "web_url": manifesto_web,
                "pdf_url": manifesto_pdf,
                "easy_read_url": easy_read_url,
                "file_url": file_url,
            }
            manifesto_obj, created = Manifesto.objects.update_or_create(
                election=election,
                party=party,
                country=country,
                language=language or "English",
                defaults=defaults,
            )
            manifesto_obj.save()
            self.write(f"{'Created' if created else 'Updated'} {manifesto_obj}")


class NationalPartyImporter(ReadFromUrlMixin, ReadFromFileMixin):
    JOINT_PARTIES = [["party:53", "joint-party:53-119"]]

    def __init__(
        self,
        election,
        force_update=False,
        from_file=False,
    ):
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

    def delete_parties(self):
        """
        Deletes NationalParty objects associated with elections for the given
        election date
        """
        count, _ = NationalParty.objects.filter(
            file_url__in=self.election.csv_files,
        ).delete()

        self.write(f"Deleted {count} local parties")

    def delete_manifestos(self):
        count, _ = Manifesto.objects.filter(
            file_url__in=self.election.csv_files,
        ).delete()

        self.write(f"Deleted {count} manifestos")

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
        First checks if the election_id is a special case or is not a full
        election ID e.g. it is made of only two parts such as local.2022-05-05.
        In this case we return all ballots for the type of election and the
        date. Otherwise attempts to find a single PostElection object for the
        election_id. If this does not exist it may be that the ID is the slug
        of an Election object so we return all ballots related to the Election.
        """

        special_cases = ["senedd", "sp", "gla"]
        election_id_list = election_id.split(".")
        election_type = election_id_list[0]
        if len(election_id_list) == 2 or election_type in special_cases:
            ballots = PostElection.objects.filter(
                ballot_paper_id__startswith=f"{election_type}.",
                election__election_date=self.election.date,
            ).exclude(localparty__parent__in=parties)
        else:
            ballots = PostElection.objects.filter(ballot_paper_id=election_id)

        if not ballots:
            # This might be an election ID, in that case,
            # apply the row to all post elections without
            # info already
            ballots = PostElection.objects.filter(
                election__slug=election_id
            ).exclude(localparty__parent__in=parties)

        return ballots.filter(personpost__party__in=parties)

    def add_national_party(self, row, party, ballots, file_url):
        """
        Takes a row of data, a Party, and a QuerySet of at least one
        PostElection objects, and creates a NationalParty for each of the ballots.
        """

        name = self.get_name(row=row)
        # only create local parties for ballots where a candidate is standing
        # for the parent party
        ballots = ballots.filter(personpost__party=party)

        for post_election in ballots.distinct():
            defaults = {
                "name": name,
                "facebook_page": row["Facebook"],
                "instagram": row["Instagram"],
                "homepage": row["Website"],
                "email": row["Email"],
                "youtube_profile_url": row.get("Youtube profile", "").strip(),
                "contact_page_url": row.get("Contact page", "").strip(),
                "party_political_broadcast": row.get(
                    "Party political broadcast", ""
                ).strip(),
                "file_url": file_url,
                "is_national": True,
            }

            _, created = NationalParty.objects.update_or_create(
                parent=party, post_election=post_election, defaults=defaults
            )
            msg = "Created" if created else "Updated"
            self.write(
                f"{msg} National Party object for {party.party_name} in {post_election.ballot_paper_id}"
            )

        self.write(f"Imported National Party objects for {name}")

    def get_name(self, row):
        """
        The sheet for Scottish/Welsh/GLA uses "Party Name" header so check for
        both
        """
        return row.get("National party name", row.get("Party Name"))

    def get_country(self, election_type):
        country_mapping = {
            "local": "Local",
            "senedd": "Wales",
            "sp": "Scotland",
        }
        return country_mapping.get(election_type, "UK")

    def import_parties(self):
        """
        This is the main action that is run by the class. First existing
        NationalParty objects for an election are deleted. Then it validates the
        row contains data we can use. Then adds a NationalParty object for each
        parent party.
        """
        self.delete_parties()
        self.delete_manifestos()

        if not self.current_elections():
            self.write(
                f"No current elections for {self.election.date}, skipping"
            )

            return

        for file_url in self.election.csv_files:
            rows = self.read_from(file_url)
            for row in rows:
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
                    election_id=row["election_id"].strip(), parties=parties
                )
                if not ballots:
                    self.write("Skipping as no ballots to use")
                    continue

                # store the PK's in a list as something strange is
                # happening later on - when trying to access
                # objects from the 'ballots' queryset after the
                # add_general_election_party method has been called, None is
                # returned instead of the object.
                # This resulted in the 'elections' queryset also
                # being empty. Storing the PK's in a list gets round
                # this but unclear why this is happening
                ballot_pks = list(ballots.values_list("pk", flat=True))
                elections = Election.objects.filter(
                    postelection__in=ballot_pks
                ).distinct()
                for party in parties:
                    self.add_national_party(row, party, ballots, file_url)
                    manifesto_web = row.get("Manifesto Website URL", "").strip()
                    manifesto_pdf = row.get("Manifesto PDF URL", "").strip()
                    if not any([manifesto_web, manifesto_pdf]):
                        self.write("No links to create Manifesto, skipping")
                        continue

                    for election in elections:
                        self.add_manifesto(row, party, election, file_url)

    def add_manifesto(self, row, party, election, file_url):
        manifesto_web = row.get("Manifesto Website URL", "").strip()
        manifesto_pdf = row.get("Manifesto PDF URL", "").strip()

        language = row.get("Manifesto Language", "English").strip()
        easy_read_url = row.get("Manifesto Easy Read PDF", "").strip()
        if any([manifesto_web, manifesto_pdf]):
            defaults = {
                "web_url": manifesto_web,
                "pdf_url": manifesto_pdf,
                "easy_read_url": easy_read_url,
                "file_url": file_url,
            }
            country = self.get_country(election_type=election.election_type)
            manifesto_obj, created = Manifesto.objects.update_or_create(
                election=election,
                party=party,
                country=country,
                language=language or "English",
                defaults=defaults,
            )
            manifesto_obj.save()
            self.write(f"{'Created' if created else 'Updated'} {manifesto_obj}")
