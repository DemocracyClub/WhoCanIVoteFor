import pytest
import vcr
from django.db.models import Count
from django.test import TestCase, override_settings
from django.urls import reverse
from elections.devs_dc_client import InvalidPostcodeError
from elections.models import PostElection
from elections.tests.factories import (
    ElectionFactory,
    PostElectionFactory,
    PostFactory,
)
from elections.views.mixins import PostcodeToPostsMixin
from elections.views.postcode_view import PostcodeView
from freezegun import freeze_time
from parishes.models import ParishCouncilElection
from pytest_django import asserts


@override_settings(
    STATICFILES_STORAGE="pipeline.storage.NonPackagingPipelineStorage",
    PIPELINE_ENABLED=False,
)
class PostcodeViewTests(TestCase):
    def setUp(self):
        self.election = ElectionFactory(
            name="City of London Corporation local election",
            election_date="2017-03-23",
            slug="local.city-of-london.2017-03-23",
        )
        self.post = PostFactory(ynr_id="LBW:E05009288", label="Aldersgate")

    @vcr.use_cassette("fixtures/vcr_cassettes/test_postcode_view.yaml")
    def test_postcode_view(self):
        response = self.client.get("/elections/EC1A4EU", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/postcode_view.html")

    @vcr.use_cassette(
        "fixtures/vcr_cassettes/test_postcode_view_with_invalid_postcode.yaml"
    )
    def test_postcode_view_with_invalid_postcode(self):
        # TE1 2ST passes postcode format validation but doesn't exist so DevsDcAPI returns a 400
        response = self.client.get("/elections/TE1 2ST", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertContains(
            response,
            "Sorry, we don't know the postcode TE1 2ST. Is there another one you can try?",
        )

    @vcr.use_cassette("fixtures/vcr_cassettes/test_uprn_view.yaml")
    def test_uprn_view(self):
        response = self.client.get(
            "/elections/WV15 6EG/10003417754/", follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/postcode_view.html")

    @vcr.use_cassette("fixtures/vcr_cassettes/test_uprn_invalid_view.yaml")
    def test_uprn_invalid_view(self):
        response = self.client.get(
            "/elections/WV15 6EG/www.somerset.gov.uk/", follow=True
        )
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")

    @vcr.use_cassette("fixtures/vcr_cassettes/test_ical_view.yaml")
    def test_ical_view(self):
        election = ElectionFactory(slug="local.cambridgeshire.2017-05-04")
        post = PostFactory(ynr_id="CED:romsey", label="Romsey")

        PostElectionFactory(post=post, election=election)
        response = self.client.get("/elections/CB13HU.ics", follow=True)
        self.assertEqual(response.status_code, 200)

    @vcr.use_cassette("fixtures/vcr_cassettes/test_ical_view.yaml")
    def test_ical_view_no_polling_station(self):
        election = ElectionFactory(slug="local.westminster.2018-11-22")
        post = PostFactory(ynr_id="lancaster-gate.by", label="Romsey")

        PostElectionFactory(
            post=post,
            election=election,
            ballot_paper_id="local.westminster.lancaster-gate.by.2018-11-22",
        )
        response = self.client.get("/elections/CB14HU.ics", follow=True)
        self.assertEqual(response.status_code, 200)

    @vcr.use_cassette("fixtures/vcr_cassettes/test_ical_view.yaml")
    def test_ical_view_address_picker(self):
        response = self.client.get("/elections/AA13AA.ics", follow=True)
        self.assertEqual(response.status_code, 200)
        assert "You may have upcoming elections" in response.content.decode()

    @vcr.use_cassette("fixtures/vcr_cassettes/test_mayor_elections.yaml")
    def test_mayor_election_postcode_lookup(self):
        election = ElectionFactory(slug="mayor.tower-hamlets.2018-05-03")
        post = PostFactory(ynr_id="tower-hamlets", label="Tower Hamlets")

        PostElectionFactory(
            post=post,
            election=election,
            ballot_paper_id="mayor.tower-hamlets.2018-05-03",
        )
        response = self.client.get("/elections/e32nx/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["postelections"].count(), 1)
        self.assertContains(response, "Tower Hamlets")

    @vcr.use_cassette("fixtures/vcr_cassettes/test_mayor_elections.yaml")
    def test_dc_logging_postcode_valid(self):
        with self.assertLogs(level="DEBUG") as captured:
            self.client.get(
                "/elections/e32nx/",
                {
                    "foo": "bar",
                    "utm_source": "test",
                    "utm_campaign": "better_tracking",
                    "utm_medium": "pytest",
                },
                HTTP_AUTHORIZATION="Token foo",
            )

        logging_message = None
        for record in captured.records:
            if record.message.startswith("dc-postcode-searches"):
                logging_message = record
        assert logging_message
        assert '"postcode": "E3 2NX"' in logging_message.message
        assert '"dc_product": "WCIVF"' in logging_message.message
        assert '"utm_source": "test"' in logging_message.message
        assert '"utm_campaign": "better_tracking"' in logging_message.message
        assert '"utm_medium": "pytest"' in logging_message.message
        assert '"calls_devs_dc_api": true' in logging_message.message

    @vcr.use_cassette(
        "fixtures/vcr_cassettes/test_dc_logging_postcode_invalid.yaml"
    )
    def test_dc_logging_postcode_invalid(self):
        with self.assertLogs(level="DEBUG") as captured:
            self.client.get(
                "/elections/INVALID/",
                {
                    "foo": "bar",
                    "utm_source": "test",
                    "utm_campaign": "better_tracking",
                    "utm_medium": "pytest",
                },
                HTTP_AUTHORIZATION="Token foo",
            )
        for record in captured.records:
            assert not record.message.startswith("dc-postcode-searches")


@pytest.mark.freeze_time("2021-05-06")
@pytest.mark.django_db
class TestPostcodeViewPolls:
    """
    Tests to check that the PostcodeView response contains correct polling
    station opening timnes
    """

    @pytest.fixture
    def mock_response(self, mocker):
        """
        Patch the get request to Every Election to return a mock that
        individual tests can then add json data to
        """
        response = mocker.MagicMock(status_code=200)
        response.json.return_value = {
            "address_picker": False,
            "dates": [],
            "electoral_services": {"identifiers": ["code"]},
            "registration": {},
        }
        mocker.patch(
            "requests.get",
            return_value=response,
            autospec=True,
        )
        return response

    def test_city_of_london_today(self, mock_response, client):
        post_election = PostElectionFactory(
            ballot_paper_id="local.city-of-london.aldgate.2021-05-06",
            election__slug="local.city-of-london.2021-05-06",
            election__election_date="2021-05-06",
            post__territory="ENG",
        )

        mock_response.json.return_value["dates"].append(
            {
                "date": post_election.election.election_date,
                "polling_station": {"polling_station_known": False},
                "ballots": [{"ballot_paper_id": post_election.ballot_paper_id}],
            }
        )

        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "e1 2ax"}), follow=True
        )
        asserts.assertContains(
            response, "Polling stations are open from 8a.m. till 8p.m. today"
        )

    def test_not_city_of_london_today(self, mock_response, client):
        post_election = PostElectionFactory(
            ballot_paper_id="local.sheffield.ecclesall.2021-05-06",
            election__slug="local.sheffield.2021-05-06",
            election__election_date="2021-05-06",
            post__territory="ENG",
        )

        mock_response.json.return_value["dates"].append(
            {
                "date": post_election.election.election_date,
                "polling_station": {"polling_station_known": False},
                "ballots": [{"ballot_paper_id": post_election.ballot_paper_id}],
            }
        )

        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "s11 8qe"}),
            follow=True,
        )
        asserts.assertContains(
            response, "Polling stations are open from 7a.m. till 10p.m. today"
        )

    def test_polling_station_opening_times(self, mock_response, client):
        post_election = PostElectionFactory(
            ballot_paper_id="local.sheffield.ecclesall.2021-05-08",
            election__slug="local.sheffield.2021-05-08",
            election__election_date="2021-05-08",
            post__territory="ENG",
        )

        mock_response.json.return_value["dates"].append(
            {
                "date": post_election.election.election_date,
                "polling_station": {
                    "polling_station_known": True,
                    "custom_finder": False,
                    "report_problem_url": "http://wheredoivote.co.uk/report_problem/?source=testing&source_url=testing",
                    "station": {
                        "id": "QK",
                        "type": "Feature",
                        "geometry": None,
                        "properties": {
                            "address": "1 Made Up Street\nMade Up Town\nMade Up County",
                            "postcode": "MA1 1AA",
                        },
                    },
                },
                "ballots": [{"ballot_paper_id": post_election.ballot_paper_id}],
            }
        )

        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "s11 8qe"}),
            follow=True,
        )
        asserts.assertContains(
            response, "It will be open from <strong>7a.m. to 10p.m.</strong>"
        )

    def test_polling_station_opening_times_city_of_london(
        self, mock_response, client
    ):
        post_election = PostElectionFactory(
            ballot_paper_id="local.city-of-london.aldgate.2021-05-08",
            election__slug="local.city-of-london.2021-05-08",
            election__election_date="2021-05-08",
            post__territory="ENG",
        )

        mock_response.json.return_value["dates"].append(
            {
                "date": post_election.election.election_date,
                "polling_station": {
                    "polling_station_known": True,
                    "custom_finder": False,
                    "report_problem_url": "http://wheredoivote.co.uk/report_problem/?source=testing&source_url=testing",
                    "station": {
                        "id": "QK",
                        "type": "Feature",
                        "geometry": None,
                        "properties": {
                            "address": "1 Made Up Street\nMade Up Town\nMade Up County",
                            "postcode": "MA1 1AA",
                        },
                    },
                },
                "ballots": [{"ballot_paper_id": post_election.ballot_paper_id}],
            }
        )

        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "e1 2ax"}), follow=True
        )
        asserts.assertContains(
            response, "It will be open from <strong>8a.m. to 8p.m.</strong>"
        )

    def test_not_today(self, mock_response, client):
        post_election = PostElectionFactory(
            election__election_date="2021-05-07",
        )

        mock_response.json.return_value["dates"].append(
            {
                "date": post_election.election.election_date,
                "polling_station": {"polling_station_known": False},
                "ballots": [{"ballot_paper_id": post_election.ballot_paper_id}],
            }
        )

        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "TE11ST"}), follow=True
        )
        asserts.assertNotContains(
            response, "Polling stations are open from 7a.m. till 10p.m. today"
        )
        asserts.assertNotContains(
            response, "Polling stations are open from 8a.m. till 8p.m. today"
        )

    @pytest.mark.django_db
    @freeze_time("2024-05-23")
    def test_multiple_elections_london(self, mock_response, client):
        """This test is for the case where there are multiple elections in
        London on the same day and we want to make sure that the correct
        polling station opening times are displayed for each election
        as well as the correct anchor links to the election pages
        """
        local_london = PostElectionFactory(
            ballot_paper_id="local.city-of-london.aldgate.2024-05-06",
            election__slug="local.city-of-london.2024-05-06",
            election__election_date="2024-05-06",
            election__name="City of London Corporation local election",
        )

        parl_london = PostElectionFactory(
            ballot_paper_id="parl.cities-of-london-and-westminster.by.2024-05-06",
            election__slug="parl.2024-05-06",
            election__election_date="2024-05-06",
            election__name="Cities of London and Westminster by-election",
        )

        mock_response.json.return_value["dates"].extend(
            [
                {
                    "date": local_london.election.election_date,
                    "polling_station": {"polling_station_known": False},
                    "ballots": [
                        {"ballot_paper_id": local_london.ballot_paper_id}
                    ],
                },
                {
                    "date": parl_london.election.election_date,
                    "polling_station": {"polling_station_known": False},
                    "ballots": [
                        {"ballot_paper_id": parl_london.ballot_paper_id}
                    ],
                },
            ]
        )

        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "TE11ST"}), follow=True
        )
        asserts.assertNotContains(
            response, "Polling stations are open from 7a.m. till 10p.m. today"
        )
        asserts.assertNotContains(
            response, "Polling stations are open from 8a.m. till 8p.m. today"
        )

        asserts.assertContains(
            response,
            '<a href="#election_local.city-of-london.2024-05-06">',
        )
        asserts.assertContains(
            response,
            '<a href="#election_parl.2024-05-06">',
        )
        # click the anchor link to the local election and check the header
        # contains the correct election name
        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "TE11ST"})
            + "#election_local.city-of-london.2024-05-06",
            follow=True,
        )
        asserts.assertContains(
            response,
            "City of London Corporation local election",
        )
        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "TE11ST"})
            + "#election_parl.2024-05-06",
            follow=True,
        )
        asserts.assertContains(
            response,
            "Cities of London and Westminster by-election",
        )

    def test_multiple_elections_not_london(self, mock_response, client):
        local = PostElectionFactory(
            ballot_paper_id="local.sheffield.ecclesall.2021-05-06",
            election__slug="local.sheffield.2021-05-06",
            election__election_date="2021-05-06",
        )
        pcc = PostElectionFactory(
            ballot_paper_id="pcc.south-yorkshire.2021-05-06",
            election__slug="pcc.south-yorkshire.2021-05-06",
            election__election_date="2021-05-06",
        )

        mock_response.json.return_value["dates"].extend(
            [
                {
                    "date": local.election.election_date,
                    "polling_station": {"polling_station_known": False},
                    "ballots": [{"ballot_paper_id": local.ballot_paper_id}],
                },
                {
                    "date": pcc.election.election_date,
                    "polling_station": {"polling_station_known": False},
                    "ballots": [{"ballot_paper_id": pcc.ballot_paper_id}],
                },
            ]
        )

        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "TE11ST"}), follow=True
        )
        assert response.status_code == 200
        asserts.assertContains(
            response, "Polling stations are open from 7a.m. till 10p.m. today"
        )
        asserts.assertNotContains(
            response, "Polling stations are open from 8a.m. till 8p.m. today"
        )
        asserts.assertTemplateUsed(response, "elections/postcode_view.html")
        asserts.assertTemplateUsed(
            response, "elections/includes/inline_elections_nav_list.html"
        )
        asserts.assertTemplateUsed(
            response, "elections/includes/_single_ballot.html"
        )

    @freeze_time("2021-04-04")
    @pytest.mark.django_db
    def test_no_polling_station_shows_council_details(
        self, mock_response, client
    ):
        """When polling station is not known,
        assert the council contact details are shown."""
        local = PostElectionFactory(
            ballot_paper_id="local.sheffield.ecclesall.2021-05-06",
            election__slug="local.sheffield.2021-05-06",
            election__election_date="2021-05-06",
            post__territory="ENG",
        )

        mock_response.json.return_value["dates"].extend(
            [
                {
                    "date": local.election.election_date,
                    "polling_station": {"polling_station_known": False},
                    "ballots": [{"ballot_paper_id": local.ballot_paper_id}],
                },
            ]
        )

        mock_response.json.return_value["electoral_services"].update(
            {
                "council_id": "W06000015",
                "name": "Cardiff Council",
                "nation": "Wales",
                "address": "Electoral Registration Officer\\nCity of Cardiff Council\\nCounty Hall Atlantic Wharf",
                "postcode": "CF10 4UW",
                "email": "info@test.com",
                "phone": "029 2087 2034",
                "website": "http://www.cardiff.gov.uk/",
            }
        )

        response = client.get(
            reverse(
                "postcode_view",
                kwargs={
                    "postcode": "TE11ST",
                },
            ),
            follow=True,
        )

        assert response.status_code == 200
        assert response.context["council"] is not None

        asserts.assertContains(
            response,
            "Cardiff Council",
        )

    def council_and_registration_details_differ(self, mock_response, client):
        """When council contact details are different from
        the registration details, show both."""
        local = PostElectionFactory(
            ballot_paper_id="local.sheffield.ecclesall.2021-05-06",
            election__slug="local.sheffield.2021-05-06",
            election__election_date="2021-05-06",
            post__territory="ENG",
        )

        mock_response.json.return_value["dates"].extend(
            [
                {
                    "date": local.election.election_date,
                    "polling_station": {"polling_station_known": False},
                    "ballots": [{"ballot_paper_id": local.ballot_paper_id}],
                },
            ]
        )

        mock_response.json.return_value["electoral_services"].update(
            {
                "council_id": "W06000015",
                "name": "Cardiff Council",
                "nation": "Wales",
                "address": "City of Cardiff Council\\nCounty Hall Atlantic Wharf",
                "postcode": "CF10 4UW",
                "email": "info@council.com",
                "phone": "029 2087 2034",
                "website": "http://www.cardiff.gov.uk/",
            }
        )

        mock_response.json.return_value["registration"].update(
            {
                "address": "Electoral Registration Officer\\nCity of Cardiff Council\\nCounty Hall Atlantic Wharf",
                "postcode": "CF10 4UW",
                "email": "info@registration.com",
                "phone": "029 2087 2034",
                "website": "http://www.cardiff.gov.uk/",
            }
        )
        response = client.get(
            reverse(
                "postcode_view",
                kwargs={
                    "postcode": "TE11ST",
                },
            ),
            follow=True,
        )

        assert response.status_code == 200
        assert response.context["registration"] is not None

        asserts.assertContains(
            response,
            "Electoral Registration Officer",
        )
        asserts.assertContains(response, "info@registration.com")
        asserts.assertContains(response, "info@council.com")


class TestPostcodeViewMethods:
    @pytest.fixture
    def view_obj(self, rf):
        """
        Returns an instance of PostcodeView
        """
        view = PostcodeView()
        request = rf.get(
            reverse("postcode_view", kwargs={"postcode": "s11 8qe"})
        )
        view.setup(request=request)

        return view

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-05-06")
    def test_get_todays_ballots(self, view_obj):
        today = PostElectionFactory(
            election__slug="election.today",
            election__election_date="2021-05-06",
        )
        tomorrow = PostElectionFactory(
            election__slug="election.tomorrow",
            election__election_date="2021-05-07",
        )
        view_obj.ballot_dict = {"ballots": PostElection.objects.all()}
        ballots = view_obj.get_todays_ballots()

        assert len(ballots) == 1
        assert today in ballots
        assert tomorrow not in ballots

    def test_get_ballot_dict(self, view_obj, mocker):
        view_obj.postcode = "E12AX"
        mocker.patch.object(
            view_obj,
            "postcode_to_ballots",
            return_value="ballots",
        )

        result = view_obj.get_ballot_dict()
        view_obj.postcode_to_ballots.assert_called_once_with(
            postcode="E12AX", uprn=None
        )
        assert result == "ballots"

    def test_get_ballot_dict_when_already_set(self, view_obj, mocker):
        view_obj.postcode = "E12AX"
        view_obj.ballot_dict = "ballots"
        mocker.patch.object(view_obj, "postcode_to_ballots")

        result = view_obj.get_ballot_dict()
        view_obj.postcode_to_ballots.assert_not_called()
        assert result == "ballots"

    @pytest.mark.django_db
    def test_multiple_london_elections_same_day(self, view_obj, mocker):
        PostElectionFactory(
            ballot_paper_id="local.city-of-london.aldgate.2021-05-06",
            election__slug="local.city-of-london.2021-05-06",
            election__election_date="2021-05-06",
            election__election_type="local",
        )
        PostElectionFactory(
            ballot_paper_id="parl.cities-of-london-and-westminster.2021-05-06",
            election__slug="parl.2021-05-06",
            election__election_date="2021-05-06",
            election__election_type="parl",
        )
        mocker.patch.object(
            view_obj,
            "get_ballots_for_next_date",
            return_value=list(PostElection.objects.all()),
        )

        assert (
            view_obj.multiple_city_of_london_elections_on_next_poll_date()
            is True
        )

    @pytest.mark.django_db
    def test_multiple_non_london_elections_same_day(self, view_obj, mocker):
        PostElectionFactory(
            election__slug="local.sheffield.2021-05-06",
            election__election_date="2021-05-06",
        )
        PostElectionFactory(
            election__slug="another.sheffield.2021-05-06",
            election__election_date="2021-05-06",
        )
        mocker.patch.object(
            view_obj,
            "get_ballots_for_next_date",
            return_value=list(PostElection.objects.all()),
        )

        assert (
            view_obj.multiple_city_of_london_elections_on_next_poll_date()
            is False
        )

    @pytest.mark.django_db
    def test_multiple_non_london_elections_same_day_single_election(
        self, view_obj, mocker
    ):
        PostElectionFactory(
            election__slug="local.city-of-london.2021-05-06",
            election__election_date="2021-05-06",
        )
        mocker.patch.object(
            view_obj,
            "get_ballots_for_next_date",
            return_value=list(PostElection.objects.all()),
        )

        assert (
            view_obj.multiple_city_of_london_elections_on_next_poll_date()
            is False
        )

    @pytest.fixture
    def post_elections(self, request):
        return self.post_elections

    @pytest.mark.django_db
    def test_show_polling_card(self, view_obj, post_elections):
        post_elections = [
            PostElectionFactory(
                election__slug="local.city-of-london.2020-05-06",
                election__election_date="2020-05-06",
                contested=True,
                cancelled=False,
            ),
            PostElectionFactory(
                election__slug="local.city-of-london.2020-05-06",
                election__election_date="2020-05-06",
                contested=False,
                cancelled=True,
            ),
        ]

        assert view_obj.show_polling_card(post_elections) is True

    @freeze_time("2020-01-01")
    @pytest.mark.django_db
    def test_global_registration_card(self, view_obj):
        post_elections = [
            PostElectionFactory(
                ballot_paper_id="local.croydon.wardname1.2020-05-06",
                election__slug="local.croydon.2020-05-06",
                election__election_date="2020-05-06",
                contested=True,
                cancelled=False,
                post__territory="ENG",
            ),
            PostElectionFactory(
                ballot_paper_id="local.croydon.wardname2.2020-05-06",
                election__slug="local.croydon.2020-05-06",
                election__election_date="2020-05-06",
                contested=False,
                cancelled=True,
                post__territory="ENG",
            ),
        ]
        card = view_obj.get_global_registration_card(
            post_elections=post_elections
        )
        assert card["show"] is True
        assert card["registration_deadline"] == "20 April 2020"
        assert card["election_date"] == "2020-05-06"

    @freeze_time("2020-01-01")
    @pytest.mark.django_db
    def test_global_postal_vote_card(self, view_obj):
        post_elections = [
            PostElectionFactory(
                ballot_paper_id="local.croydon.wardname1.2020-05-06",
                election__slug="local.croydon.2020-05-06",
                election__election_date="2020-05-06",
                contested=True,
                cancelled=False,
                post__territory="ENG",
            ),
            PostElectionFactory(
                ballot_paper_id="local.croydon.wardname2.2020-05-06",
                election__slug="local.croydon.2020-05-06",
                election__election_date="2020-05-06",
                contested=False,
                cancelled=True,
                post__territory="ENG",
            ),
        ]
        card = view_obj.get_global_postal_vote_card(
            post_elections=post_elections, council={"council_id": "EXE"}
        )
        assert card["show"] is True
        assert card["before_application_deadline"] is True
        assert card["application_deadline"] == "21 April 2020"
        assert card["election_date"] == "2020-05-06"

    def test_num_ballots_no_parish_election(self, view_obj, mocker):
        future_post_election = mocker.MagicMock(spec=PostElection, past_date=0)
        past_post_election = mocker.MagicMock(spec=PostElection, past_date=1)
        view_obj.ballot_dict = {
            "ballots": [future_post_election, past_post_election]
        }
        assert view_obj.num_ballots() == 1

    def test_num_ballots_with_contested_parish_election(self, view_obj, mocker):
        future_post_election = mocker.MagicMock(spec=PostElection, past_date=0)
        past_post_election = mocker.MagicMock(spec=PostElection, past_date=1)
        parish_council_election = mocker.MagicMock(
            spec=ParishCouncilElection,
            in_past=False,
            is_contested=True,
        )
        view_obj.ballot_dict = {
            "ballots": [future_post_election, past_post_election]
        }
        view_obj.parish_council_election = parish_council_election
        assert view_obj.num_ballots() == 2

    def test_num_ballots_with_uncontested_parish_election(
        self, view_obj, mocker
    ):
        future_post_election = mocker.MagicMock(spec=PostElection, past_date=0)
        past_post_election = mocker.MagicMock(spec=PostElection, past_date=1)
        parish_council_election = mocker.MagicMock(
            spec=ParishCouncilElection,
            in_past=False,
            is_contested=False,
        )
        view_obj.ballot_dict = {
            "ballots": [future_post_election, past_post_election]
        }
        view_obj.parish_council_election = parish_council_election
        assert view_obj.num_ballots() == 1

    def test_num_ballots_with_is_contested_none_parish_election(
        self, view_obj, mocker
    ):
        future_post_election = mocker.MagicMock(spec=PostElection, past_date=0)
        past_post_election = mocker.MagicMock(spec=PostElection, past_date=1)
        parish_council_election = mocker.MagicMock(
            spec=ParishCouncilElection,
            in_past=False,
            is_contested=None,
        )
        view_obj.ballot_dict = {
            "ballots": [future_post_election, past_post_election]
        }
        view_obj.parish_council_election = parish_council_election
        assert view_obj.num_ballots() == 1

    def test_num_ballots_with_parish_election_in_past(self, view_obj, mocker):
        future_post_election = mocker.MagicMock(spec=PostElection, past_date=0)
        past_post_election = mocker.MagicMock(spec=PostElection, past_date=1)
        parish_council_election = mocker.MagicMock(
            spec=ParishCouncilElection,
            in_past=True,
            is_contested=True,
        )
        view_obj.ballot_dict = {
            "ballots": [future_post_election, past_post_election]
        }
        view_obj.parish_council_election = parish_council_election
        assert view_obj.num_ballots() == 1

    def test_get_parish_council_election_when_already_assigned(
        self, view_obj, mocker
    ):
        """
        Test if view has a parish_council_election set it is returned
        """
        parish_council_election = mocker.MagicMock(spec=ParishCouncilElection)
        view_obj.parish_council_election = parish_council_election

        result = view_obj.get_parish_council_election()
        assert result is parish_council_election

    @pytest.mark.django_db
    def test_get_parish_council_election_none(self, view_obj):
        """
        Test if there is no parish council related to views ballots that None
        is returned
        """
        post_election = PostElectionFactory()
        post_election.num_parish_councils = 0
        view_obj.ballot_dict = {
            "ballots": PostElection.objects.annotate(
                num_parish_councils=Count("parish_councils")
            )
        }

        result = view_obj.get_parish_council_election()
        assert result is None
        assert view_obj.parish_council_election is None

    @pytest.mark.django_db
    def test_get_parish_council_election_object_returned(self, view_obj):
        """
        Test if there is a parish council related to views ballots that it is
        returned
        """
        post_election = PostElectionFactory()
        post_election.num_parish_councils = 0
        parish_council_election = ParishCouncilElection.objects.create()
        parish_council_election.ballots.add(post_election)
        view_obj.ballot_dict = {
            "ballots": PostElection.objects.annotate(
                num_parish_councils=Count("parish_councils")
            )
        }

        result = view_obj.get_parish_council_election()
        assert result == parish_council_election
        assert view_obj.parish_council_election == parish_council_election

    @pytest.mark.django_db
    def test_get_voter_id_status_id_required(self, view_obj, mocker):
        post_election_requires_id = mocker.MagicMock(
            spec=PostElection, requires_voter_id="EA-2022", cancelled=False
        )
        post_election_no_id = mocker.MagicMock(
            spec=PostElection, requires_voter_id=None, cancelled=False
        )
        view_obj.ballot_dict = {
            "ballots": [post_election_requires_id, post_election_no_id]
        }
        assert view_obj.get_voter_id_status() == "EA-2022"

    @pytest.mark.django_db
    def test_get_voter_id_status_id_not_required(self, view_obj, mocker):
        post_election_no_id = mocker.MagicMock(
            spec=PostElection, requires_voter_id=None, cancelled=False
        )
        view_obj.ballot_dict = {
            "ballots": [post_election_no_id, post_election_no_id]
        }
        assert view_obj.get_voter_id_status() is None

    def test_show_parish_text_true(self, view_obj):
        view_obj.postcode = "s11 8qe"
        council_context = {"identifiers": ["code"]}
        assert view_obj.show_parish_text(council_context) is True

    @pytest.mark.parametrize(
        "ni_postcodes", ["BT1 1AA", "BT93 8AD", "BT60 4PU"]
    )
    def test_show_parish_text_false_for_NI_postcodes(
        self, ni_postcodes, view_obj
    ):
        view_obj.postcode = ni_postcodes
        council_context = {"identifiers": ["code"]}
        assert view_obj.show_parish_text(council_context) is False

    @pytest.mark.parametrize("lnd_gss", ["E09000011", "E09000012", "E09000013"])
    def test_show_parish_text_false_for_lnd_boroughs(self, lnd_gss, view_obj):
        view_obj.postcode = "postcode"
        council_context = {"identifiers": [lnd_gss]}
        assert view_obj.show_parish_text(council_context) is False


class TestPostcodeiCalView:
    def test_invalid_postcode_redirects(self, mocker, client):
        mocker.patch.object(
            PostcodeToPostsMixin,
            "postcode_to_ballots",
            side_effect=InvalidPostcodeError,
        )
        # TE1 1ST is a known (fake) postcode, TE1 2ST is not.
        url = reverse("postcode_ical_view", kwargs={"postcode": "TE1 2ST"})
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == "/?invalid_postcode=1&postcode=TE1%202ST"

    def test_ical_with_election(self, mocker, client):
        mocker.patch.object(
            PostcodeToPostsMixin,
            "postcode_to_ballots",
            side_effect=InvalidPostcodeError,
        )
        url = reverse("postcode_ical_view", kwargs={"postcode": "TE1 1ST"})
        response = client.get(url)

        assert response.status_code == 200
        content_without_ephemeral_datestamp = "\n".join(
            line
            for line in response.content.decode("utf-8")
            .replace("\r\n", "\n")
            .split("\n")
            if "DTSTAMP" not in line
        )
        assert (
            content_without_ephemeral_datestamp
            == """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Elections in TE1 1ST//mxm.dk//
SUMMARY:Elections in TE1 1ST
X-WR-CALNAME:Elections in TE1 1ST
X-WR-TIMEZONE:Europe/London
BEGIN:VEVENT
SUMMARY:Llantalbot local election - Made-Up-Ward
DTSTART;TZID=Europe/London:20240704T070000
DTEND;TZID=Europe/London:20240704T220000
UID:-local.faketown.2024-07-04
DESCRIPTION:Find out more at https://whocanivotefor.co.uk/elections/TE11ST
 /
GEO:-3.119229\;51.510885
LOCATION:1 Made Up Street\\, Made Up Town\\, Made Up County\\, MA1 1AA
END:VEVENT
END:VCALENDAR
"""
        )
