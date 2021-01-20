import sys
from functools import update_wrapper

from django.db import transaction
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.timezone import datetime, timedelta
from django.utils.http import urlencode
from uk_election_timetables.election_ids import from_election_id
from uk_election_timetables.calendars import Country

import requests


class EEHelper:

    ee_cache = {}

    @property
    def base_elections_url(self):
        """
        Builds the URL for the elections endpoint of EveryElection API
        """
        return f"{settings.EE_BASE}/api/elections/"

    @cached_property
    def deleted_election_ids(self):
        """
        Returns a generator object that retreives ids for elections that have
        been deleted in Every Election. Accepts optional date arg, otherwise
        defaults to objects with a Poll Open date within the last fifty days
        """
        params = {
            "deleted": 1,
            "poll_open_date__gte": datetime.now().date() - timedelta(days=50),
        }
        querystring = urlencode(params)
        url = f"{self.base_elections_url}?{querystring}"
        pages = JsonPaginator(page1=url, stdout=sys.stdout)
        for page in pages:
            return [result["election_id"] for result in page["results"]]

    @transaction.atomic
    def delete_deleted_elections(self):
        """
        Deletes Election and PostElection objects that were soft-deleted in
        EveryElection
        """
        from elections.models import (
            Election,
            PostElection,
        )  # noqa avoid circular import

        elections_count, _ = Election.objects.filter(
            slug__in=self.deleted_election_ids,
            current=False,
        ).delete()

        post_elections_count, _ = PostElection.objects.filter(
            ballot_paper_id__in=self.deleted_election_ids,
        ).delete()

        return elections_count, post_elections_count

    def prewarm_cache(self, current=False):
        page1 = self.base_elections_url
        if current:
            page1 = f"{page1}?current=True"
        pages = JsonPaginator(page1, sys.stdout)
        for page in pages:
            for result in page["results"]:
                self.ee_cache[result["election_id"]] = result

    def get_data(self, election_id):
        if election_id in self.ee_cache:
            return self.ee_cache[election_id]
        req = requests.get(f"{self.base_elections_url}{election_id}/")
        if req.status_code == 200:
            self.ee_cache[election_id] = req.json()
            return self.ee_cache[election_id]
        else:
            self.ee_cache[election_id] = None
        return None


class JsonPaginator:
    def __init__(self, page1, stdout):
        self.next_page = page1
        self.stdout = stdout

    def __iter__(self):
        while self.next_page:
            self.stdout.write(self.next_page)

            r = requests.get(self.next_page)
            if r.status_code != 200:
                self.stdout.write("crashing with response:")
                self.stdout.write(r.text)
            r.raise_for_status()
            data = r.json()

            try:
                self.next_page = data["next"]
            except KeyError:
                self.next_page = None

            yield data

        return


class ElectionIDSwitcher:
    def __init__(self, ballot_view, election_view, **initkwargs):
        self.election_id_kwarg = initkwargs.get("election_id_kwarg", "election")
        self.ballot_view = ballot_view
        self.election_view = election_view

    def __call__(self, request, *args, **kwargs):
        from elections.models import PostElection

        ballot_qs = PostElection.objects.filter(
            ballot_paper_id=kwargs[self.election_id_kwarg]
        )

        if ballot_qs.exists():
            # This is a ballot paper ID
            view_cls = self.ballot_view
        else:
            # Assume this is an election ID, or let the election_view
            # deal with the 404
            view_cls = self.election_view

        view = view_cls.as_view()

        view.view_class = view_cls
        # take name and docstring from class
        update_wrapper(view, view_cls, updated=())
        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, view_cls.dispatch, assigned=())

        self.__name__ = self.__qualname__ = view.__name__
        return view(request, *args, **kwargs)


def expected_sopn_publish_date(slug, territory):
    country = {
        "ENG": Country.ENGLAND,
        "WLS": Country.WALES,
        "SCT": Country.SCOTLAND,
        "NIR": Country.NORTHERN_IRELAND,
    }

    if slug.startswith("local") and territory not in country:
        return None

    try:
        return from_election_id(slug, country[territory]).sopn_publish_date
    except BaseException:
        return None
