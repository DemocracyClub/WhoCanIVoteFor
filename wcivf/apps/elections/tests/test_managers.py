import pytest

from django.test import TestCase
from elections.tests.factories import ElectionFactoryLazySlug
from elections.models import Election


class TestElectionManager(TestCase):
    @pytest.mark.freeze_time("2021-1-14")
    def test_past(self):
        """
        Asset that non-current elections with a past election date are returned
        """
        current_future = ElectionFactoryLazySlug(
            current=True, election_date="2021-5-6"
        )
        not_current_future = ElectionFactoryLazySlug(
            current=False,
            election_date="2021-5-6",
        )
        current_past = ElectionFactoryLazySlug(
            current=True, election_date="2021-1-1"
        )
        not_current_past = ElectionFactoryLazySlug(
            current=False, election_date="2021-1-1"
        )

        qs = Election.objects.past()
        assert qs.count() == 1
        self.assertNotIn(current_future, qs)
        self.assertNotIn(not_current_future, qs)
        self.assertNotIn(current_past, qs)
        self.assertIn(not_current_past, qs)
