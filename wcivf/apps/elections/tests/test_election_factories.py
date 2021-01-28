from django.test import TestCase
from django.utils.text import slugify

from elections.tests.factories import (
    ElectionFactory,
    PostFactory,
    PostElectionFactory,
    ElectionFactoryLazySlug,
)

from elections.models import Election, Post, PostElection


class TestFactories(TestCase):
    """
    Meta tests to ensure that the factories are working
    """

    def _test_save(self, model, factory):
        self.assertEqual(model.objects.all().count(), 0)
        created_model = factory.create()
        self.assertEqual(model.objects.all().count(), 1)
        return created_model

    def test_election_factory(self):
        model = self._test_save(Election, ElectionFactory)
        self.assertEqual(model.name, "UK General Election 2015")

    def test_post_factory(self):
        model = self._test_save(Post, PostFactory)
        self.assertEqual(model.label, "copeland")

    def test_post_election_factory(self):
        self.assertEqual(Election.objects.all().count(), 0)
        self.assertEqual(Post.objects.all().count(), 0)
        self._test_save(PostElection, PostElectionFactory)
        self.assertEqual(Election.objects.all().count(), 1)
        self.assertEqual(Post.objects.all().count(), 1)

    def test_election_lazy_slug(self):
        """
        Test generated slug can be used to reverse url
        """
        election = ElectionFactoryLazySlug.build()
        slug = election.slug
        name = slugify(election.name)
        assert election.get_absolute_url() == f"/elections/{slug}/{name}/"
