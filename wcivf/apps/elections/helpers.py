import sys
from functools import update_wrapper

from django.conf import settings
from sopn_publish_date import StatementPublishDate, Country
from datetime import datetime

import requests


class EEHelper:

    ee_cache = {}

    def prewarm_cache(self, current=False):
        page1 = "{}/api/elections/".format(settings.EE_BASE)
        if current:
            page1 = "{}?current=True".format(page1)
        pages = JsonPaginator(page1, sys.stdout)
        for page in pages:
            for result in page["results"]:
                self.ee_cache[result["election_id"]] = result

    def get_data(self, election_id):
        if election_id in self.ee_cache:
            return self.ee_cache[election_id]
        req = requests.get(
            "{}/api/elections/{}/".format(settings.EE_BASE, election_id)
        )
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

    if not expected_sopn_publish_date.lookup:
        expected_sopn_publish_date.lookup = StatementPublishDate()

    if slug.startswith("local") and territory not in country:
        return None

    try:
        if slug.startswith("local") and territory is not None:

            date_of_poll = datetime.strptime(
                slug.split(".")[-1], "%Y-%m-%d"
            ).date()

            return expected_sopn_publish_date.lookup.local(
                date_of_poll, country=country[territory]
            )
        else:
            return expected_sopn_publish_date.lookup.for_id(slug)
    except BaseException:
        return None


expected_sopn_publish_date.lookup = None
