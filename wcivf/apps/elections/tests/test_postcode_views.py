import pytest
import vcr

from django.conf import settings
from django.db.models import Count
from django.urls import reverse
from django.test import TestCase, override_settings
from pytest_django import asserts
from elections.models import PostElection, InvalidPostcodeError

from elections.tests.factories import (
    ElectionFactory,
    PostFactory,
    PostElectionFactory,
)
from core.models import LoggedPostcode, write_logged_postcodes
from elections.views.mixins import PostcodeToPostsMixin
from elections.views.postcode_view import PostcodeView
from unittest import skipIf

from parishes.models import ParishCouncilElection


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

    @vcr.use_cassette("fixtures/vcr_cassettes/test_postcode_view.yaml")
    @override_settings(REDIS_KEY_PREFIX="WCIVF_TEST")
    @skipIf(settings.REDIS_LOG_POSTCODE is False, "Dependant on redis running")
    def test_logged_postcodes(self):
        assert LoggedPostcode.objects.all().count() == 0
        response = self.client.get("/elections/EC1A4EU", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/postcode_view.html")
        assert LoggedPostcode.objects.all().count() == 0
        write_logged_postcodes()
        assert LoggedPostcode.objects.all().count() == 1

    @vcr.use_cassette("fixtures/vcr_cassettes/test_ical_view.yaml")
    def test_ical_view(self):
        election = ElectionFactory(slug="local.cambridgeshire.2017-05-04")
        post = PostFactory(ynr_id="CED:romsey", label="Romsey")

        PostElectionFactory(post=post, election=election)
        response = self.client.get("/elections/CB13HU.ics", follow=True)
        self.assertEqual(response.status_code, 200)

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
        response.json.return_value = {"results": []}
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
        )
        mock_response.json.return_value["results"].append(
            {"election_id": post_election.ballot_paper_id}
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
        )
        mock_response.json.return_value["results"].append(
            {"election_id": post_election.ballot_paper_id}
        )

        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "s11 8qe"}),
            follow=True,
        )
        asserts.assertContains(
            response, "Polling stations are open from 7a.m. till 10p.m. today"
        )

    def test_not_today(self, mock_response, client):
        post_election = PostElectionFactory(
            election__election_date="2021-05-07",
        )
        mock_response.json.return_value["results"].append(
            {"election_id": post_election.ballot_paper_id}
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

    def test_multiple_elections_london(self, mock_response, client):
        local_london = PostElectionFactory(
            ballot_paper_id="local.city-of-london.aldgate.2021-05-06",
            election__slug="local.city-of-london.2021-05-06",
            election__election_date="2021-05-06",
        )
        parl_london = PostElectionFactory(
            ballot_paper_id="parl.cities-of-london-and-westminster.by.2021-05-06",
            election__slug="parl.2021-05-06",
            election__election_date="2021-05-06",
        )
        mock_response.json.return_value["results"] = [
            {"election_id": local_london.ballot_paper_id},
            {"election_id": parl_london.ballot_paper_id},
        ]

        response = client.get(
            reverse("postcode_view", kwargs={"postcode": "TE11ST"}), follow=True
        )
        asserts.assertNotContains(
            response, "Polling stations are open from 7a.m. till 10p.m. today"
        )
        asserts.assertNotContains(
            response, "Polling stations are open from 8a.m. till 8p.m. today"
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
        mock_response.json.return_value["results"] = [
            {"election_id": local.ballot_paper_id},
            {"election_id": pcc.ballot_paper_id},
        ]

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
        view_obj.ballots = PostElection.objects.all()
        ballots = view_obj.get_todays_ballots()

        assert len(ballots) == 1
        assert today in ballots
        assert tomorrow not in ballots

    def test_get_ballots(self, view_obj, mocker):
        view_obj.postcode = "E12AX"
        mocker.patch.object(
            view_obj,
            "postcode_to_ballots",
            return_value="ballots",
        )

        result = view_obj.get_ballots()
        view_obj.postcode_to_ballots.assert_called_once_with(postcode="E12AX")
        assert result == "ballots"

    def test_get_ballots_when_already_set(self, view_obj, mocker):
        view_obj.postcode = "E12AX"
        view_obj.ballots = "ballots"
        mocker.patch.object(view_obj, "postcode_to_ballots")

        result = view_obj.get_ballots()
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
            "get_todays_ballots",
            return_value=list(PostElection.objects.all()),
        )

        assert view_obj.multiple_city_of_london_elections_today() is True

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
            "get_todays_ballots",
            return_value=list(PostElection.objects.all()),
        )

        assert view_obj.multiple_city_of_london_elections_today() is False

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
            "get_todays_ballots",
            return_value=list(PostElection.objects.all()),
        )

        assert view_obj.multiple_city_of_london_elections_today() is False

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

    def test_num_ballots_no_parish_election(self, view_obj, mocker):
        future_post_election = mocker.MagicMock(spec=PostElection, past_date=0)
        past_post_election = mocker.MagicMock(spec=PostElection, past_date=1)
        view_obj.ballots = [future_post_election, past_post_election]
        assert view_obj.num_ballots() == 1

    def test_num_ballots_with_contested_parish_election(self, view_obj, mocker):
        future_post_election = mocker.MagicMock(spec=PostElection, past_date=0)
        past_post_election = mocker.MagicMock(spec=PostElection, past_date=1)
        parish_council_election = mocker.MagicMock(
            spec=ParishCouncilElection,
            in_past=False,
            is_contested=True,
        )
        view_obj.ballots = [future_post_election, past_post_election]
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
        view_obj.ballots = [future_post_election, past_post_election]
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
        view_obj.ballots = [future_post_election, past_post_election]
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
        view_obj.ballots = [future_post_election, past_post_election]
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
        view_obj.ballots = PostElection.objects.annotate(
            num_parish_councils=Count("parish_councils")
        )

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
        view_obj.ballots = PostElection.objects.annotate(
            num_parish_councils=Count("parish_councils")
        )

        result = view_obj.get_parish_council_election()
        assert result == parish_council_election
        assert view_obj.parish_council_election == parish_council_election


class TestPostcodeiCalView:
    def test_invalid_postcode_redirects(self, mocker, client):
        mocker.patch.object(
            PostcodeToPostsMixin,
            "postcode_to_ballots",
            side_effect=InvalidPostcodeError,
        )
        url = reverse("postcode_ical_view", kwargs={"postcode": "TE1 1ST"})
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == "/?invalid_postcode=1&postcode=TE1%201ST"
