import vcr
from django.core.cache import cache
from elections.tests.factories import (
    ElectionFactory,
    PostElectionFactory,
    PostFactory,
)
from parties.tests.factories import PartyFactory
from people.tests.factories import PersonFactory, PersonPostFactory
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase


class TestAPIBasics(APITestCase):
    def test_200_on_api_base(self):
        req = self.client.get(reverse("api:api-root"))
        assert req.status_code == 200

    def test_candidates_for_postcode_view_raises_error(self):
        req = self.client.get(reverse("api:candidates-for-postcode-list"))
        assert req.status_code == 400
        assert req.data == {"detail": "postcode is a required GET parameter"}


class TestAPISearchViews(APITestCase):
    def setUp(self):
        cache.clear()

        self.election = ElectionFactory(
            name="2017 General Election",
            election_date="2017-06-08",
            slug="parl.2017-06-08",
            any_non_by_elections=True,
        )
        self.post = PostFactory(
            ynr_id="WMC:E14000639", label="Cities of London and Westminster"
        )
        self.post_election = PostElectionFactory(
            ballot_paper_id="parl.cities-of-london-and-westminster.2017-06-08",
            post=self.post,
            election=self.election,
        )
        self.post_election.modified = "2023-01-01T00:00:00Z"
        self.post_election.save(update_modified=False)
        PersonFactory.reset_sequence()
        person = PersonFactory()
        pe = PostElectionFactory(election=self.election, post=self.post)
        PersonPostFactory(
            post_election=pe,
            election=self.election,
            person=person,
            post=self.post,
            party=PartyFactory(),
        )
        self.expected_response = [
            {
                "ballot_paper_id": "parl.cities-of-london-and-westminster.2017-06-08",
                "absolute_url": "http://testserver/elections/parl.cities-of-london-and-westminster.2017-06-08/cities-of-london-and-westminster/",
                "election_date": "2017-06-08",
                "election_id": "parl.2017-06-08",
                "election_name": "2017 General Election",
                "post": {
                    "post_name": "Cities of London and Westminster",
                    "post_slug": "WMC:E14000639",
                },
                "cancelled": False,
                "postal_voting_requirements": "RPA2000",
                "replaced_by": None,
                "seats_contested": 1,
                "requires_voter_id": None,
                "organisation_type": "local-authority",
                "voting_system": {"name": "", "slug": ""},
                "ballot_locked": False,
                "hustings": None,
                "last_updated": "2023-01-01T00:00:00Z",
                "by_election_reason": "",
                "candidates": [
                    {
                        "list_position": None,
                        "party": {
                            "party_id": "PP01",
                            "party_name": "Test Party",
                        },
                        "person": {
                            "absolute_url": "http://testserver/person/0/candidate-0",
                            "ynr_id": 0,
                            "name": "Candidate 0",
                            "email": None,
                            "photo_url": None,
                            "leaflets": None,
                        },
                        "previous_party_affiliations": None,
                    }
                ],
            }
        ]

    @vcr.use_cassette("fixtures/vcr_cassettes/test_postcode_view.yaml")
    def test_candidates_for_postcode_view(self):
        url = reverse("api:candidates-for-postcode-list")
        with self.assertNumQueries(6):
            req = self.client.get("{}?postcode=EC1A4EU".format(url))
        assert req.status_code == 200
        assert req.json() == self.expected_response

    def test_candidates_for_ballots(self):
        url = reverse("api:candidates-for-ballots-list")
        with self.assertNumQueries(6):
            req = self.client.get(
                "{}?ballot_ids=parl.cities-of-london-and-westminster.2017-06-08".format(
                    url
                )
            )
        assert req.status_code == 200
        assert req.json() == self.expected_response

    def test_candidates_for_ballots_modified_gt(self):
        url = reverse("api:candidates-for-ballots-list")
        with self.assertNumQueries(6):
            req = self.client.get("{}?modified_gt=1832-06-07".format(url))
        assert req.status_code == 200
        assert req.json() == self.expected_response

    def test_candidates_for_ballots_modified_gt_future_date_no_respnse(self):
        url = reverse("api:candidates-for-ballots-list")
        with self.assertNumQueries(1):
            req = self.client.get("{}?modified_gt=2232-06-07".format(url))
        assert req.status_code == 200
        assert req.json() == []

    @vcr.use_cassette("fixtures/vcr_cassettes/test_postcode_view.yaml")
    def test_lock_status(self):
        self.post_election.locked = True
        self.post_election.save()
        url = reverse("api:candidates-for-postcode-list")
        req = self.client.get("{}?postcode=EC1A4EU".format(url))
        assert req.status_code == 200
        assert req.json()[0]["ballot_locked"] is True

    def test_party_description_used_as_party_name_for_list_elections(self):
        list_election = ElectionFactory(
            name="2021 Scottish Parliament Election",
            election_date="2021-05-06",
            slug="sp.r.2021-05-06",
            uses_lists=True,
        )
        post = PostFactory(ynr_id="sp.r:lothian", label="Lothian")
        post_election = PostElectionFactory(
            ballot_paper_id="sp.r.lothian.2021-05-06",
            post=post,
            election=list_election,
        )
        party = PartyFactory(
            party_id="PP02", party_name="Conservative and Unionist Party"
        )
        person = PersonFactory()
        PersonPostFactory(
            post_election=post_election,
            election=list_election,
            person=person,
            post=post,
            party=party,
            party_name="Conservative and Unionist Party",
            party_description_text="Scottish Conservative and Unionist Party",
        )
        url = reverse("api:candidates-for-ballots-list")
        req = self.client.get(
            "{}?ballot_ids=sp.r.lothian.2021-05-06".format(url)
        )
        assert req.status_code == 200
        candidate = req.json()[0]["candidates"][0]
        assert (
            candidate["party"]["party_name"]
            == "Scottish Conservative and Unionist Party"
        )

    def test_party_name_used_when_description_is_empty_for_list_elections(self):
        list_election = ElectionFactory(
            name="2021 Scottish Parliament Election",
            election_date="2021-05-06",
            slug="sp.r.2021-05-06",
            uses_lists=True,
        )
        post = PostFactory(ynr_id="sp.r:lothian", label="Lothian")
        post_election = PostElectionFactory(
            ballot_paper_id="sp.r.lothian.2021-05-06",
            post=post,
            election=list_election,
        )
        party = PartyFactory(
            party_id="PP02", party_name="Conservative and Unionist Party"
        )
        person = PersonFactory()
        PersonPostFactory(
            post_election=post_election,
            election=list_election,
            person=person,
            post=post,
            party=party,
            party_name="Conservative and Unionist Party",
            party_description_text="",
        )
        url = reverse("api:candidates-for-ballots-list")
        req = self.client.get(
            "{}?ballot_ids=sp.r.lothian.2021-05-06".format(url)
        )
        assert req.status_code == 200
        candidate = req.json()[0]["candidates"][0]
        assert (
            candidate["party"]["party_name"]
            == "Conservative and Unionist Party"
        )

    def test_list_election_candidates_ordered_by_description_not_name(self):
        list_election = ElectionFactory(
            name="2021 Scottish Parliament Election",
            election_date="2021-05-06",
            slug="sp.r.2021-05-06",
            uses_lists=True,
        )
        post = PostFactory(ynr_id="sp.r:lothian", label="Lothian")
        post_election = PostElectionFactory(
            ballot_paper_id="sp.r.lothian.2021-05-06",
            post=post,
            election=list_election,
        )
        snp = PartyFactory(
            party_id="PP90", party_name="Scottish National Party"
        )
        con = PartyFactory(
            party_id="PP91", party_name="Conservative and Unionist Party"
        )
        PersonPostFactory(
            post_election=post_election,
            election=list_election,
            person=PersonFactory(),
            post=post,
            party=snp,
            party_name="Scottish National Party",
            party_description_text="Alba Party",
            list_position=1,
        )
        PersonPostFactory(
            post_election=post_election,
            election=list_election,
            person=PersonFactory(),
            post=post,
            party=con,
            party_name="Conservative and Unionist Party",
            party_description_text="Scottish Conservative and Unionist Party",
            list_position=1,
        )
        url = reverse("api:candidates-for-ballots-list")
        req = self.client.get(
            "{}?ballot_ids=sp.r.lothian.2021-05-06".format(url)
        )
        assert req.status_code == 200
        candidates = req.json()[0]["candidates"]
        party_names = [c["party"]["party_name"] for c in candidates]
        assert party_names == [
            "Alba Party",
            "Scottish Conservative and Unionist Party",
        ]
