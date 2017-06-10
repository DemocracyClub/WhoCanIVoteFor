"""
Tests for the HTML of the site.

Used for making sure meta tags and important information is actually
shown before and after template changes.
"""


from django.test import TestCase
from django.core.management import call_command

import vcr

from people.models import PersonPost
from results.models import ResultEvent

from people.tests.factories import PersonFactory, PersonPostFactory
from elections.tests.factories import (
    ElectionFactory, PostFactory, PostElectionFactory)


class TestResults(TestCase):

    def setUp(self):
        self.election = ElectionFactory(
            name="2017 General Election",
            election_date="2017-06-08",
            slug="parl.2017-06-08",
        )
        winners = [
            {
                'person_id': 2809,
                'post_id': 'WMC:E14000803',
                'post_label': 'Maidenhead',
            },
            {
                'person_id': 357,
                'post_id': 'WMC:E14000608',
                'post_label': 'Buckingham',
            },
            {
                'person_id': 2811,
                'post_id': 'WMC:E14000803',
                'post_label': 'Maidenhead',
            },
            {
                'person_id': 34291,
                'post_id': 'WMC:E14000673',
                'post_label': 'Dulwich and West Norwood',
            },
        ]

        for person_info in winners:
            person = PersonFactory(pk=person_info['person_id'])
            post = PostFactory(
                ynr_id=person_info['post_id'],
                label=person_info['post_label']
            )
            PostElectionFactory(
                post=post,
                election=self.election
            )

            PersonPostFactory(
                person=person,
                election=self.election,
                post=post
            )

    @vcr.use_cassette(
        'fixtures/vcr_cassettes/test_results_atom_feed.yaml')
    def test_results_atom_feed(self):
        assert PersonPost.objects.filter(elected=True).count() == 0
        assert ResultEvent.objects.all().count() == 0
        call_command('import_results_atom')
        # We saw 4 elements in the Atom feed, but one was retracted
        assert PersonPost.objects.filter(elected=True).count() == 3
        assert ResultEvent.objects.all().count() == 3

        req = self.client.get('/results/')
        assert req.status_code == 200
        self.assertContains(req, 'Maidenhead')

