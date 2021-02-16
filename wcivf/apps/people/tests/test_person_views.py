import pytest

from django.test import TestCase
from django.test.utils import override_settings
from unittest.mock import MagicMock

from people.tests.factories import PersonFactory, PersonPostFactory
from parties.tests.factories import PartyFactory
from elections.tests.factories import (
    ElectionFactory,
    PostFactory,
    PostElectionFactory,
)
from people.views import PersonView


@override_settings(
    STATICFILES_STORAGE="pipeline.storage.NonPackagingPipelineStorage",
    PIPELINE_ENABLED=False,
)
class PersonViewTests(TestCase):
    def setUp(self):
        self.party = PartyFactory()
        self.person = PersonFactory()
        self.person_url = self.person.get_absolute_url()

    def test_current_person_view(self):
        self.personpost = PersonPostFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "people/person_detail.html")
        self.assertNotContains(
            response, '<meta name="robots" content="noindex">'
        )

    def test_not_current_person_view(self):
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "people/not_current_person_detail.html"
        )
        self.assertContains(response, "Previous elections")
        self.assertNotContains(response, "Contact information")
        self.assertContains(response, '<meta name="robots" content="noindex">')

    def test_not_current_person_with_twfy_id(self):
        self.person.twfy_id = 10999
        self.person.save()
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "people/person_detail.html")
        self.assertNotContains(
            response, '<meta name="robots" content="noindex">'
        )
        self.assertContains(response, "Record in office")
        self.assertContains(response, "TheyWorkForYou")

    def test_correct_elections_listed(self):
        response = self.client.get(self.person_url, follow=True)

        election_name = "FooBar Election 2017"

        self.assertNotContains(response, election_name)
        election = ElectionFactory(
            name=election_name,
            current=True,
            election_date="2040-01-01",
            slug="local.foobar.2040-01-01",
        )
        post = PostFactory()
        pe = PostElectionFactory(
            election=election,
            post=post,
            ballot_paper_id="local.foo.bar.2040-01-01",
        )
        PersonPostFactory(
            post_election=pe,
            election=election,
            person=self.person,
            party=self.party,
        )

        response = self.client.get(self.person_url, follow=True)
        self.assertContains(response, election_name)
        self.assertContains(response, "is the")

    def test_election_in_past_listed(self):
        response = self.client.get(self.person_url, follow=True)

        election_name = "FooBar Election 2017"

        self.assertNotContains(response, election_name)
        election = ElectionFactory(
            name=election_name,
            current=False,
            election_date="2017-01-01",
            slug="local.foobar.2017-01-01",
        )
        post = PostFactory()
        pe = PostElectionFactory(
            election=election,
            post=post,
            ballot_paper_id="local.foo.bar.2017-01-01",
        )
        PersonPostFactory(
            post_election=pe,
            election=election,
            person=self.person,
            party=self.party,
        )

        response = self.client.get(self.person_url, follow=True)
        self.assertContains(response, election_name)
        self.assertContains(response, "was the")


class TestPersonViewUnitTests:
    @pytest.fixture
    def view_obj(self, rf):
        """
        Return an instance of PersonView set up with a fake request object
        """
        request = rf.get("/person/1/")
        view = PersonView()
        view.setup(request=request)
        return view

    @pytest.mark.parametrize(
        "object, expected",
        [
            (MagicMock(twfy_id=10999), "people/person_detail.html"),
            (
                MagicMock(current_or_future_candidacies=True),
                "people/person_detail.html",
            ),
            (
                MagicMock(current_or_future_candidacies=False, twfy_id=None),
                "people/not_current_person_detail.html",
            ),
        ],
    )
    def test_get_template_names(self, view_obj, object, expected):
        view_obj.object = object
        assert view_obj.get_template_names() == [expected]
