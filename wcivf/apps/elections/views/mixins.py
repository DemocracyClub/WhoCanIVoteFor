import json
from datetime import date, datetime
from typing import Optional

from core.utils import LastWord
from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, Count, F, IntegerField, Prefetch, When
from django.db.models.functions import Coalesce
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from elections.constants import (
    PEOPLE_FOR_BALLOT_KEY_FMT,
    UPDATED_SLUGS,
)
from elections.devs_dc_client import DevsDCAPIException, DevsDCClient
from hustings.models import Husting
from leaflets.models import Leaflet
from uk_election_timetables.calendars import Country
from uk_election_timetables.election import TimetableEvent
from uk_election_timetables.election_ids import from_election_id

DEVS_DC_CLIENT = DevsDCClient()


class PostcodeToPostsMixin(object):
    def get(self, request, *args, **kwargs):
        from ..models import InvalidPostcodeError

        try:
            context = self.get_context_data(**kwargs)
        except (InvalidPostcodeError, DevsDCAPIException):
            return HttpResponseRedirect(
                "/?invalid_postcode=1&postcode={}".format(self.postcode)
            )
        return self.render_to_response(context)

    def postcode_to_ballots(self, postcode, uprn=None, compact=False):
        kwargs = {"postcode": postcode}
        if uprn:
            kwargs["uprn"] = uprn
        parl_boundary_changes = getattr(
            settings, "SHOW_PARL_BOUNDARY_CHANGES", False
        )
        if parl_boundary_changes:
            kwargs["parl_boundaries"] = 1
        results_json = DEVS_DC_CLIENT.make_request(**kwargs)
        all_ballots = []
        ret = {
            "address_picker": results_json["address_picker"],
            "polling_station": {},
            "electoral_services": results_json["electoral_services"],
            "registration": results_json["registration"],
            "postcode_location": json.dumps(
                results_json.get("postcode_location", "")
            ),
        }

        if parl_boundary_changes:
            ret["parl_boundary_changes"] = results_json.get(
                "parl_boundary_changes", None
            )

        if ret["address_picker"]:
            ret["addresses"] = results_json["addresses"]
            return ret

        for election_date in results_json.get("dates"):
            for ballot in election_date.get("ballots", []):
                all_ballots.append(ballot["ballot_paper_id"])
            if election_date["polling_station"]["polling_station_known"]:
                ret["polling_station_known"] = True
                ret["polling_station"] = election_date["polling_station"]

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

        pes = pes.prefetch_related(
            Prefetch("husting_set", queryset=Husting.objects.published())
        )
        pes = pes.order_by(
            "past_date", "election__election_date", "-election__election_weight"
        )
        ret["ballots"] = pes
        return ret


class PostelectionsToPeopleMixin(object):
    def people_for_ballot(self, postelection, compact=False):
        key = PEOPLE_FOR_BALLOT_KEY_FMT.format(
            postelection.ballot_paper_id, compact
        )
        people_for_post = cache.get(key)
        if people_for_post:
            return people_for_post
        people_for_post = postelection.personpost_set.all()
        people_for_post = people_for_post.annotate(
            last_name=LastWord("person__name")
        )
        people_for_post = people_for_post.annotate(
            name_for_ordering=Coalesce("person__sort_name", "last_name")
        )
        if postelection.election.uses_lists:
            order_by = ["party__party_name", "list_position"]
        else:
            order_by = ["name_for_ordering", "person__name"]

        people_for_post = people_for_post.order_by(
            F("elected").desc(nulls_last=True),
            F("votes_cast").desc(nulls_last=True),
            *order_by,
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
    def show_polling_card(self, post_elections):
        return any(p.contested and not p.cancelled for p in post_elections)

    def get_advance_voting_station_info(self, polling_station: Optional[dict]):
        if not polling_station or not polling_station.get(
            "advance_voting_station"
        ):
            return None
        advance_voting_station = polling_station["advance_voting_station"]

        last_open_row = advance_voting_station["opening_times"][-1]
        last_date, last_open, last_close = last_open_row
        open_in_future = (
            datetime.combine(
                datetime.strptime(last_date, "%Y-%m-%d").date(),
                datetime.strptime(last_close, "%H:%M:%S").time(),
            )
            > datetime.now()
        )
        advance_voting_station["open_in_future"] = open_in_future
        return advance_voting_station

    def get_global_registration_card(self, post_elections):
        # City of London local elections have different
        # registration rules to every other election
        non_city_of_london_ballots = [
            ballot
            for ballot in post_elections
            if not ballot.election.is_city_of_london_local_election
            and not ballot.cancelled
        ]

        if not non_city_of_london_ballots:
            return False
        next_ballot = non_city_of_london_ballots[0]
        election = next_ballot.election
        country = next_ballot.post.territory

        if not country:
            country = Country.ENGLAND
        else:
            country = {
                "ENG": Country.ENGLAND,
                "SCT": Country.SCOTLAND,
                "WLS": Country.WALES,
                "NIR": Country.NORTHERN_IRELAND,
            }.get(country)
        election = from_election_id(election_id=election.slug, country=country)
        event = TimetableEvent.REGISTRATION_DEADLINE
        return {
            "show": election.is_before(event),
            "registration_deadline": next_ballot.registration_deadline,
            "election_date": next_ballot.election.election_date,
        }


class LogLookUpMixin(object):
    def log_postcode(self: View, postcode):
        entry = settings.POSTCODE_LOGGER.entry_class(
            postcode=postcode,
            dc_product=settings.POSTCODE_LOGGER.dc_product.wcivf,
            calls_devs_dc_api=True,
            **self.request.session.get("utm_data"),
        )
        settings.POSTCODE_LOGGER.log(entry)


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
