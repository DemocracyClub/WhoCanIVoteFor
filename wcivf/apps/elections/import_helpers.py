import sys
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction

from elections.helpers import JsonPaginator, EEHelper
from elections.models import PostElection, Election, Post, VotingSystem
from people.models import Person, PersonPost


class YNRElectionImporter:
    """
    Takes a JSON object from YNR and creates or updates an election object
    from it.

    Manages caching, and updating metadata from EE

    """

    def __init__(self, ee_helper=None):
        if not ee_helper:
            ee_helper = EEHelper()
        self.ee_helper = ee_helper
        self.election_cache = {}

    def update_or_create_from_ballot_dict(self, ballot_dict):
        created = False
        slug = ballot_dict["election"]["election_id"]

        if slug not in self.election_cache:
            election_type = slug.split(".")[0]

            election_weight = 10
            if ballot_dict["election"]["party_lists_in_use"]:
                election_weight = 20
            if election_type == "mayor":
                election_weight = 5

            election, created = Election.objects.update_or_create(
                slug=slug,
                election_type=slug.split(".")[0],
                defaults={
                    "election_date": ballot_dict["election"]["election_date"],
                    "name": ballot_dict["election"]["name"],
                    "current": ballot_dict["election"]["current"],
                    "election_weight": election_weight,
                },
            )

            self.import_metadata_from_ee(election)
            self.election_cache[election.slug] = election
        return self.election_cache[slug]

    def import_metadata_from_ee(self, election):
        """
        There are various things we don't have in YNR, have in EE and want here

        This means grabbing the data from EE directly
        """
        ee_data = self.ee_helper.get_data(election.slug)
        if ee_data:
            updated = False
            metadata = ee_data["metadata"]
            if metadata:
                election.metadata = metadata
                updated = True

            description = ee_data["explanation"]
            if description:
                election.description = description
                updated = True

            voting_system = ee_data["voting_system"]
            if voting_system:
                election.voting_system = VotingSystem.objects.update_or_create(
                    slug=voting_system["slug"],
                    defaults={"name": voting_system["name"]},
                )[0]
                updated = True

            if updated:
                election.save()


class YNRPostImporter:
    def __init__(self, ee_helper=None):
        if not ee_helper:
            ee_helper = EEHelper()
        self.ee_helper = ee_helper
        self.post_cache = {}

    def update_or_create_from_ballot_dict(self, ballot_dict):
        created = False
        if not ballot_dict["post"]["slug"] in self.post_cache:
            post, created = Post.objects.update_or_create(
                ynr_id=ballot_dict["post"]["slug"],
                defaults={"label": ballot_dict["post"]["label"]},
            )
            self.post_cache[post.ynr_id] = post
        return self.post_cache[ballot_dict["post"]["slug"]]


class YNRBallotImporter:
    """
    Class for populating local election and ballot models in this
    project from YNR.

    The class sets up everything needed for show a ballot, including elections,
    posts, voting systems, and the person information that show's on a ballot.
    (name, candidacy data)

    """

    def __init__(
        self,
        force_update=False,
        stdout=sys.stdout,
        current_only=False,
        exclude_candidacies=False,
        force_metadata=False,
    ):
        self.stdout = stdout
        self.ee_helper = EEHelper()
        self.election_importer = YNRElectionImporter(self.ee_helper)
        self.post_imporer = YNRPostImporter(self.ee_helper)
        self.force_update = force_update
        self.current_only = current_only
        self.exclude_candidacies = exclude_candidacies
        self.force_metadata = force_metadata

    def get_paginator(self, page1):
        return JsonPaginator(page1, self.stdout)

    def do_import(self, params=None):
        default_params = {"page_size": "200"}
        if self.current_only:
            default_params["current"] = True
        if params:
            default_params.update(params)
        else:
            prewarm_current_only = True
            if self.force_metadata:
                prewarm_current_only = False
            self.ee_helper.prewarm_cache(current=prewarm_current_only)

        querystring = urlencode(default_params)
        if not params and not self.current_only:
            # this is a full import, use the cache
            url = (
                settings.YNR_BASE
                + "/media/cached-api/latest/ballots-000001.json"
            )
        else:
            url = settings.YNR_BASE + "/api/next/ballots/?{}".format(
                querystring
            )
        pages = self.get_paginator(url)

        for page in pages:
            self.add_ballots(page)
        if not params:
            # Don't try to do things like add replaced
            # ballots if we've filtered the ballots.
            # This is because there's a high chance we've not
            # got all the ballots we need yet.
            self.run_post_ballot_import_tasks()

    @transaction.atomic()
    def add_ballots(self, results):

        for ballot_dict in results["results"]:
            print(ballot_dict["ballot_paper_id"])

            election = self.election_importer.update_or_create_from_ballot_dict(
                ballot_dict
            )

            post = self.post_imporer.update_or_create_from_ballot_dict(
                ballot_dict
            )

            ballot, created = PostElection.objects.update_or_create(
                ballot_paper_id=ballot_dict["ballot_paper_id"],
                defaults={
                    "election": election,
                    "post": post,
                    "winner_count": ballot_dict["winner_count"],
                    "cancelled": ballot_dict["cancelled"],
                    "locked": ballot_dict["candidates_locked"],
                },
            )

            if ballot.election.current or self.force_metadata:
                self.import_metadata_from_ee(ballot)

            if not self.exclude_candidacies:
                # Now set the nominations up for this ballot
                # First, remove any old candidates, this is to flush out candidates
                # that have changed. We just delete the `person_post`
                # (`membership` in YNR), not the person profile.
                ballot.personpost_set.all().delete()
                for candidate in ballot_dict["candidacies"]:
                    person, person_created = Person.objects.update_or_create(
                        ynr_id=candidate["person"]["id"],
                        defaults={"name": candidate["person"]["name"]},
                    )
                    PersonPost.objects.create(
                        post_election=ballot,
                        person=person,
                        party_id=candidate["party"]["legacy_slug"],
                        list_position=candidate["party_list_position"],
                        elected=candidate["elected"],
                        post=ballot.post,
                        election=ballot.election,
                    )

            if created:
                self.stdout.write(
                    "Added new ballot: {0}".format(ballot.ballot_paper_id)
                )

    def import_metadata_from_ee(self, ballot):
        # First, grab the data from EE

        self.set_territory(ballot)
        self.set_voting_system(ballot)
        self.set_metadata(ballot)
        ballot.save()

    def set_territory(self, ballot):
        if ballot.post.territory and not self.force_update:
            return
        ee_data = self.ee_helper.get_data(ballot.ballot_paper_id)
        if ee_data and "organisation" in ee_data:
            territory = ee_data["organisation"].get("territory_code", "-")
        else:
            territory = "-"

        ballot.post.territory = territory
        ballot.post.save()

    def set_voting_system(self, ballot):
        if ballot.voting_system_id and not self.force_update:
            return
        ee_data = self.ee_helper.get_data(ballot.ballot_paper_id)
        if ee_data and "voting_system" in ee_data:
            ballot.voting_system_id = ee_data["voting_system"]["slug"]
            ballot.save()

    def set_metadata(self, ballot):
        if ballot.metadata and not self.force_update:
            return
        ee_data = self.ee_helper.get_data(ballot.ballot_paper_id)
        if ee_data:
            ballot.metadata = ee_data["metadata"]

    def run_post_ballot_import_tasks(self):
        self.attach_cancelled_ballot_info()

    def get_replacement_ballot(self, ballot_id):
        replacement_ballot = None
        ee_data = self.ee_helper.get_data(ballot_id)
        if ee_data:
            replacement_ballot_id = ee_data["replaced_by"]
            if replacement_ballot_id:
                replacement_ballot = PostElection.objects.get(
                    ballot_paper_id=replacement_ballot_id
                )
        return replacement_ballot

    def attach_cancelled_ballot_info(self):
        # we need to do this as a post-process instead of in the manager
        # because if we're going to link 2 PostElection objects together
        # we need to be sure that both of them already exist in our DB
        cancelled_ballots = PostElection.objects.filter(cancelled=True)

        for cb in cancelled_ballots:
            cb.replaced_by = self.get_replacement_ballot(cb.ballot_paper_id)
            # Always get metadata, even if we might have it already.
            # This is because is self.force_update is False, it might not have
            # been imported already
            cb.metadata = self.set_metadata(cb)
            cb.save()
