from datetime import date

import requests
from django.db.models import F, Prefetch
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.core.cache import cache
from django.db.models import IntegerField
from django.db.models import When, Case, Count
from django.urls import reverse

from core.models import log_postcode
from core.utils import LastWord
from leaflets.models import Leaflet
from people.models import PersonPost
from elections.constants import UPDATED_SLUGS

from elections.constants import (
    POSTCODE_TO_BALLOT_KEY_FMT,
    PEOPLE_FOR_BALLOT_KEY_FMT,
    POLLING_STATIONS_KEY_FMT,
)


class PostcodeToPostsMixin(object):
    def get(self, request, *args, **kwargs):
        from ..models import InvalidPostcodeError

        try:
            context = self.get_context_data(**kwargs)
        except InvalidPostcodeError:
            return HttpResponseRedirect(
                "/?invalid_postcode=1&postcode={}".format(self.postcode)
            )
        return self.render_to_response(context)

    def postcode_to_ballots(self, postcode, compact=False):
        key = POSTCODE_TO_BALLOT_KEY_FMT.format(postcode.replace(" ", ""))
        results_json = cache.get(key)
        if not results_json:
            url = "{0}/api/elections?postcode={1}&current=1".format(
                settings.EE_BASE, postcode
            )
            req = requests.get(url)

            # Don't cache bad postcodes
            from ..models import InvalidPostcodeError

            if req.status_code != 200:
                raise InvalidPostcodeError(postcode)

            results_json = req.json()["results"]
            cache.set(key, results_json)

        all_ballots = []
        for election in results_json:
            ballot_paper_id = election["election_id"]
            all_ballots.append(ballot_paper_id)

        from ..models import PostElection

        pes = PostElection.objects.filter(ballot_paper_id__in=all_ballots)
        pes = pes.annotate(
            past_date=Case(
                When(election__election_date__lt=date.today(), then=1),
                When(election__election_date__gte=date.today(), then=0),
                output_field=IntegerField(),
            )
        )
        # majority of ballots will have 0 so do this now to help reduce
        # unnecessary DB queries later on
        pes = pes.annotate(
            num_parish_councils=Count("parish_councils"),
        )
        pes = pes.select_related("post")
        pes = pes.select_related("election")
        pes = pes.select_related("election__voting_system")
        pes = pes.select_related("referendum")

        pes = pes.prefetch_related("husting_set")
        pes = pes.order_by(
            "past_date", "election__election_date", "-election__election_weight"
        )

        return pes


class PostelectionsToPeopleMixin(object):
    def people_for_ballot(self, postelection, compact=False):
        key = PEOPLE_FOR_BALLOT_KEY_FMT.format(
            postelection.ballot_paper_id, compact
        )
        people_for_post = cache.get(key)
        if people_for_post:
            return people_for_post

        people_for_post = PersonPost.objects.filter(post_election=postelection)
        people_for_post = people_for_post.annotate(
            last_name=LastWord("person__name")
        )

        if postelection.election.uses_lists:
            order_by = ["party__party_name", "list_position"]
        else:
            order_by = ["person__sort_name", "last_name", "person__name"]

        people_for_post = people_for_post.order_by(
            F("elected").desc(nulls_last=True), *order_by
        )
        people_for_post = people_for_post.select_related(
            "post",
            "election",
            "person",
            "party",
        )
        people_for_post = people_for_post.prefetch_related(
            "previous_party_affiliations"
        )
        people_for_post = people_for_post.prefetch_related(
            Prefetch(
                "person__leaflet_set",
                queryset=Leaflet.objects.order_by(
                    "date_uploaded_to_electionleaflets"
                ),
                to_attr="ordered_leaflets",
            )
        )
        if not compact:
            people_for_post = people_for_post.prefetch_related(
                "person__pledges"
            )
        cache.set(key, people_for_post)
        return people_for_post


class PollingStationInfoMixin(object):
    def get_polling_station_info(self, postcode):
        key = POLLING_STATIONS_KEY_FMT.format(postcode.replace(" ", ""))
        info = cache.get(key)
        if info:
            return info

        info = {}
        base_url = settings.WDIV_BASE + settings.WDIV_API
        url = "{}/postcode/{}.json?auth_token={}".format(
            base_url,
            postcode,
            getattr(settings, "WDIV_API_KEY", "DCINTERNAL-WHO"),
        )
        try:
            req = requests.get(url)
        except:
            return info
        if req.status_code != 200:
            return info
        info.update(req.json())
        cache.set(key, info)
        return info

    def show_polling_card(self, post_elections):
        for p in post_elections:
            if p.contested and not p.cancelled:
                return True
        return False


class LogLookUpMixin(object):
    def log_postcode(self, postcode):
        kwargs = {"postcode": postcode}
        kwargs.update(self.request.session["utm_data"])
        log_postcode(kwargs)


class NewSlugsRedirectMixin(object):
    def get_changed_election_slug(self, slug):
        return UPDATED_SLUGS.get(slug, slug)

    def get(self, request, *args, **kwargs):
        given_slug = self.kwargs.get(self.pk_url_kwarg)
        updated_slug = self.get_changed_election_slug(given_slug)
        if updated_slug != given_slug:
            return HttpResponsePermanentRedirect(
                reverse("election_view", kwargs={"election": updated_slug})
            )

        return super().get(request, *args, **kwargs)
