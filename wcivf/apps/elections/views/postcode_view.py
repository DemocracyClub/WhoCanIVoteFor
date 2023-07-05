from icalendar import Calendar, Event, vText
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import TemplateView, View
from typing import Optional

from core.helpers import clean_postcode
from elections.dummy_models import DummyPostElection
from parishes.models import ParishCouncilElection
from .mixins import (
    LogLookUpMixin,
    PostcodeToPostsMixin,
    PollingStationInfoMixin,
    PostelectionsToPeopleMixin,
    NewSlugsRedirectMixin,
)
from elections.models import InvalidPostcodeError
from ..devs_dc_client import DevsDCAPIException


class PostcodeView(
    NewSlugsRedirectMixin,
    PostcodeToPostsMixin,
    PollingStationInfoMixin,
    LogLookUpMixin,
    TemplateView,
    PostelectionsToPeopleMixin,
):
    """
    This is the main view that takes a postcode and shows all elections
    for that area, with related information.

    This is really the main destination page of the whole site, so there is a
    high chance this will need to be split out in to a few mixins, and cached
    well.
    """

    template_name = "elections/postcode_view.html"
    pk_url_kwarg = "postcode"
    ballot_dict = None
    postcode = None
    uprn = None
    parish_council_election = None

    def get_ballot_dict(self):
        """
        Returns a QuerySet of PostElection objects. Calls postcode_to_ballots
        and updates the self.ballot_dict attribute the first time it is called.
        """
        if self.ballot_dict is None:
            self.ballot_dict = self.postcode_to_ballots(
                postcode=self.postcode, uprn=self.uprn
            )

        return self.ballot_dict

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.postcode = clean_postcode(kwargs["postcode"])
        self.uprn = self.kwargs.get("uprn")
        self.log_postcode(self.postcode)

        context["postcode"] = self.postcode

        try:
            ballot_dict = self.get_ballot_dict()
            context["address_picker"] = ballot_dict.get("address_picker")
            context["addresses"] = ballot_dict.get("addresses")
        except (InvalidPostcodeError, DevsDCAPIException) as exception:
            raise exception

        entry = settings.POSTCODE_LOGGER.entry_class(
            postcode=self.postcode,
            dc_product=settings.POSTCODE_LOGGER.dc_product.wcivf,
            **self.request.session.get("utm_data"),
        )
        settings.POSTCODE_LOGGER.log(entry)

        if context["address_picker"]:
            return context

        context["postelections"] = ballot_dict.get("ballots")
        context["show_polling_card"] = self.show_polling_card(
            context["postelections"]
        )
        context["people_for_post"] = {}
        for postelection in context["postelections"]:
            postelection.people = self.people_for_ballot(postelection)
        context["polling_station"] = self.ballot_dict.get("polling_station")

        context[
            "advance_voting_station"
        ] = self.get_advance_voting_station_info(context["polling_station"])

        context["ballots_today"] = self.get_todays_ballots()
        context[
            "multiple_city_of_london_elections_today"
        ] = self.multiple_city_of_london_elections_today()
        context["referendums"] = list(self.get_referendums())
        context["parish_council_election"] = self.get_parish_council_election()
        context["num_ballots"] = self.num_ballots()
        context["requires_voter_id"] = self.get_voter_id_status()

        return context

    def get_todays_ballots(self):
        """
        Return a list of ballots filtered by whether they are today
        """
        return [
            ballot
            for ballot in self.ballot_dict.get("ballots")
            if ballot.election.is_election_day
        ]

    def get_referendums(self):
        """
        Yield all referendums associated with the ballots for this postcode.
        After 6th May return an empty list to avoid displaying unwanted
        information
        """
        if (
            timezone.datetime.today().date()
            > timezone.datetime(2021, 5, 6).date()
        ):
            return []

        for ballot in self.ballot_dict.get("ballots", []):
            yield from ballot.referendums.all()

    def multiple_city_of_london_elections_today(self):
        """
        Checks if there are multiple elections taking place today in the City
        of London. This is used to determine if it is safe to display polling
        station open/close times in the template. As if there are multiple then
        it is unclear what time the polls would be open. See this issue for
        more info https://github.com/DemocracyClub/WhoCanIVoteFor/issues/441
        """
        ballots = self.get_todays_ballots()

        # if only one ballot can return early
        if len(ballots) <= 1:
            return False

        if not any(
            [ballot for ballot in ballots if ballot.election.is_city_of_london]
        ):
            return False

        # get unique elections and return whether more than 1
        return len({ballot.election.slug for ballot in ballots}) > 1

    def get_parish_council_election(self):
        """
        Check if we have any ballot_dict with a parish council, if not return an
        empty QuerySet. If we do, return the first object we find. This may seem
        arbritary to only use the first object we find but in practice we only
        assign a single parish council for to a single english local election
        ballot. So in practice we should only ever find one object.
        """
        if self.parish_council_election is not None:
            return self.parish_council_election
        if not self.ballot_dict.get("ballots"):
            return None

        ballots_with_parishes = self.ballot_dict.get("ballots").filter(
            num_parish_councils__gt=0
        )
        if not ballots_with_parishes:
            return None

        self.parish_council_election = ParishCouncilElection.objects.filter(
            ballots__in=self.ballot_dict["ballots"]
        ).first()
        return self.parish_council_election

    def num_ballots(self):
        """
        Calculate the number of ballot_dict there will be to fill in, accounting for
        the any parish council ballot_dict if a contested parish council election is
        taking place in the future
        """
        num_ballots = len(
            [
                ballot
                for ballot in self.ballot_dict.get("ballots")
                if not ballot.past_date
            ]
        )

        if not self.parish_council_election:
            return num_ballots

        if self.parish_council_election.in_past:
            return num_ballots

        if self.parish_council_election.is_contested:
            num_ballots += 1

        return num_ballots

    def get_voter_id_status(self) -> Optional[str]:
        """
        For a given election, determine whether any ballot_dict require photo ID
        If yes, return the stub value (e.g. EA-2022)
        If no, return None
        """
        for ballot in self.ballot_dict.get("ballots"):
            if not ballot.cancelled and (voter_id := ballot.requires_voter_id):
                return voter_id
        return None


class PostcodeiCalView(
    NewSlugsRedirectMixin, PostcodeToPostsMixin, View, PollingStationInfoMixin
):

    pk_url_kwarg = "postcode"

    def get(self, request, *args, **kwargs):
        postcode = kwargs["postcode"]
        uprn = kwargs.get("uprn")
        try:
            self.ballot_dict = self.postcode_to_ballots(
                postcode=postcode, uprn=uprn
            )
        except (InvalidPostcodeError, DevsDCAPIException):
            return HttpResponseRedirect(
                f"/?invalid_postcode=1&postcode={postcode}"
            )

        polling_station = self.ballot_dict.get("polling_station")

        cal = Calendar()
        cal["summary"] = "Elections in {}".format(postcode)
        cal["X-WR-CALNAME"] = "Elections in {}".format(postcode)
        cal["X-WR-TIMEZONE"] = "Europe/London"

        cal.add("version", "2.0")
        cal.add("prodid", "-//Elections in {}//mxm.dk//".format(postcode))

        # If we need the user to enter an address then we
        # need to add an event asking them to do this.
        # This is a bit of a hack, but there's no real other
        # way to tell the user about address pickers
        if self.ballot_dict.get("address_picker", False):
            event = Event()
            event["uid"] = f"{postcode}-address-picker"
            event["summary"] = "You may have upcoming elections"
            event.add("dtstamp", timezone.now())
            event.add("dtstart", timezone.now().date())
            event.add("dtend", timezone.now().date())
            event.add(
                "DESCRIPTION",
                (
                    f"In order to tell you about upcoming elections you need to"
                    f"pick your address from a list and update your calender feed URL"
                    f"Please visit https://whocanivotefor.co.uk/elections/{postcode}/, pick your"
                    f"address and then use the calendar URL on that page."
                ),
            )
            cal.add_component(event)
            return HttpResponse(cal.to_ical(), content_type="text/calendar")

        for post_election in self.ballot_dict["ballots"]:
            if post_election.cancelled:
                continue
            event = Event()
            event["uid"] = "{}-{}".format(
                post_election.post.ynr_id, post_election.election.slug
            )
            event["summary"] = "{} - {}".format(
                post_election.election.name, post_election.post.label
            )
            event.add("dtstamp", timezone.now())
            event.add("dtstart", post_election.election.start_time)
            event.add("dtend", post_election.election.end_time)
            event.add(
                "DESCRIPTION",
                "Find out more at {}/elections/{}/".format(
                    settings.CANONICAL_URL, postcode.replace(" ", "")
                ),
            )

            if polling_station.get("polling_station_known"):
                geometry = polling_station["station"]["geometry"]
                if geometry:
                    event["geo"] = "{};{}".format(
                        geometry["coordinates"][0], geometry["coordinates"][1]
                    )
                properties = polling_station["station"]["properties"]
                event["location"] = vText(
                    "{}, {}".format(
                        properties["address"].replace("\n", ", "),
                        properties["postcode"],
                    )
                )

            cal.add_component(event)

            # add hustings events if there are any in the future
            for husting in post_election.husting_set.future():
                event = Event()
                event["uid"] = husting.uuid
                event["summary"] = husting.title
                event.add("dtstamp", timezone.now())
                event.add("dtstart", husting.starts)
                if husting.ends:
                    event.add("dtend", husting.ends)
                event.add("DESCRIPTION", f"Find out more at {husting.url}")
                cal.add_component(event)

        return HttpResponse(cal.to_ical(), content_type="text/calendar")


class DummyPostcodeView(PostcodeView):
    postcode = None

    def get(self, request, *args, **kwargs):
        kwargs["postcode"] = self.postcode
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = kwargs
        self.postcode = clean_postcode(kwargs["postcode"])
        context["postcode"] = self.postcode
        context["postelections"] = self.get_ballot_dict()
        context["show_polling_card"] = True
        context["polling_station"] = {}
        context["num_ballots"] = 1

        return context

    def get_ballot_dict(self):
        return [DummyPostElection()]
