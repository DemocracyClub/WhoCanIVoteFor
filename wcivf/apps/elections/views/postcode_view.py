from typing import Optional

from administrations.helpers import AdministrationsHelper
from core.helpers import clean_postcode
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.generic import TemplateView, View
from elections.devs_dc_client import InvalidPostcodeError, InvalidUprnError
from elections.dummy_models import DummyPostElection, dummy_polling_station
from elections.models import LOCAL_TZ
from icalendar import Calendar, Event, vText
from parishes.models import ParishCouncilElection

from .mixins import (
    LogLookUpMixin,
    NewSlugsRedirectMixin,
    PollingStationInfoMixin,
    PostcodeToPostsMixin,
    PostelectionsToPeopleMixin,
)


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

        context["postcode"] = self.postcode

        ballot_dict = self.get_ballot_dict()
        context["address_picker"] = ballot_dict.get("address_picker")
        context["addresses"] = ballot_dict.get("addresses")

        if (
            not context["address_picker"]
            and settings.ENABLE_LAYERS_OF_STATE_FEATURE
        ):
            try:
                administrations = AdministrationsHelper(
                    self.postcode, uprn=self.uprn
                )
                context["administrations"] = administrations
                if administrations.address_picker:
                    context["address_picker"] = True
                    context["addresses"] = administrations.addresses
            except Exception:
                # Just catch any error at the moment, as we don't want this to break anything
                pass

        if context["address_picker"]:
            return context

        context["postelections"] = ballot_dict.get("ballots")

        had_election = False
        if len(context["postelections"]) > 0:
            had_election = True
        self.log_postcode(self.postcode, had_election)

        context["future_postelections"] = self.future_postelections(
            context["postelections"]
        )
        context["show_polling_card"] = self.show_polling_card(
            context["postelections"]
        )
        context["global_registration_card"] = self.get_global_registration_card(
            context["postelections"]
        )
        context["people_for_post"] = {}
        for postelection in context["postelections"]:
            postelection.people = self.people_for_ballot(postelection)
        context["polling_station"] = self.ballot_dict.get("polling_station")
        context[
            "polling_station_opening_times"
        ] = self.get_polling_station_opening_times()
        context["council"] = self.ballot_dict.get("electoral_services")
        context["registration"] = self.ballot_dict.get("registration")
        context["postcode_location"] = self.ballot_dict.get(
            "postcode_location", None
        )
        context["global_postal_vote_card"] = self.get_global_postal_vote_card(
            context["postelections"], context["council"]
        )

        context[
            "advance_voting_station"
        ] = self.get_advance_voting_station_info(context["polling_station"])

        context["ballots_today"] = self.get_todays_ballots()
        context[
            "multiple_city_of_london_elections_on_next_poll_date"
        ] = self.multiple_city_of_london_elections_on_next_poll_date()
        context["referendums"] = list(self.get_referendums())
        context["parish_council_election"] = self.get_parish_council_election()
        context["num_ballots"] = self.num_ballots()
        context["requires_voter_id"] = self.get_voter_id_status()
        context["show_parish_text"] = self.show_parish_text(context["council"])

        return context

    def future_postelections(self, postelections):
        """
        Given a list of postelections, check if any of them are in the future
        and return True if so.
        """
        return any(
            postelection
            for postelection in postelections
            if not postelection.election.in_past
        )

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

    def get_ballots_for_next_date(self):
        ballots = (
            self.get_ballot_dict()
            .get("ballots")
            .order_by("election__election_date")
        )
        if not ballots:
            return ballots
        first_ballot_date = ballots[0].election.election_date
        return ballots.filter(election__election_date=first_ballot_date)

    def get_polling_station_opening_times(self):
        ballots = self.get_ballots_for_next_date()
        if not ballots:
            return {
                "polls_open": None,
                "polls_close": None,
            }
        for ballot in ballots:
            if ballot.election.is_city_of_london_local_election:
                return {
                    "polls_open": ballot.election.polls_open,
                    "polls_close": ballot.election.polls_close,
                }
        return {
            "polls_open": ballots[0].election.polls_open,
            "polls_close": ballots[0].election.polls_close,
        }

    def multiple_city_of_london_elections_on_next_poll_date(self):
        """
        Checks if there are multiple elections taking place today in the City
        of London. This is used to determine if it is safe to display polling
        station open/close times in the template. As if there are multiple then
        it is unclear what time the polls would be open. See this issue for
        more info https://github.com/DemocracyClub/WhoCanIVoteFor/issues/441
        """
        ballots = self.get_ballots_for_next_date()

        # if only one ballot can return early
        if len(ballots) <= 1:
            return False

        if not any(
            ballot
            for ballot in ballots
            if ballot.election.is_city_of_london_local_election
            or ballot.election.election_covers_city_of_london
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

    def show_parish_text(self, council):
        """
        Returns True if the postcode isn't in London and Northern Ireland. We don't want
        to show the parish council text in these areas because they don't have them.
        """
        # all NI postcodes start with BT
        if self.postcode.startswith("BT"):
            return False
        # All London borough GSS codes start with E09
        if any(
            identifier.startswith("E09")
            for identifier in council["identifiers"]
        ):
            return False
        return True


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
        except InvalidPostcodeError:
            return HttpResponseRedirect(
                f"/?invalid_postcode=1&postcode={postcode}"
            )
        except InvalidUprnError:
            raise Http404()

        polling_station = self.ballot_dict.get("polling_station")

        cal = Calendar()
        cal["summary"] = "Elections in {}".format(postcode)
        cal["X-WR-CALNAME"] = "Elections in {}".format(postcode)
        cal["X-WR-TIMEZONE"] = LOCAL_TZ.zone

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
            PostcodeiCalView.add_local_timestamp(
                event, "dtstart", timezone.now().date()
            )
            PostcodeiCalView.add_local_timestamp(
                event, "dtend", timezone.now().date()
            )
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
            PostcodeiCalView.add_local_timestamp(
                event, "dtstart", post_election.election.start_time
            )
            PostcodeiCalView.add_local_timestamp(
                event, "dtend", post_election.election.end_time
            )
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
            for husting in post_election.husting_set.published().future():
                event = Event()
                event["uid"] = husting.uuid
                event["summary"] = husting.title
                event.add("dtstamp", timezone.now())
                PostcodeiCalView.add_local_timestamp(
                    event, "dtstart", husting.starts
                )
                if husting.ends:
                    PostcodeiCalView.add_local_timestamp(
                        event, "dtend", husting.ends
                    )
                event.add("DESCRIPTION", f"Find out more at {husting.url}")
                cal.add_component(event)

        return HttpResponse(cal.to_ical(), content_type="text/calendar")

    @staticmethod
    def add_local_timestamp(event, name, value):
        event.add(name, value, {"TZID": LOCAL_TZ.zone})


class DummyPostcodeiCalView(PostcodeiCalView):
    def get(self, request, *args, **kwargs):
        kwargs["postcode"] = "TE1 1ST"
        return super().get(request, *args, **kwargs)

    def postcode_to_ballots(self, postcode, uprn=None, compact=False):
        return {
            "ballots": [DummyPostElection()],
            "polling_station": dummy_polling_station,
        }


class DummyPostcodeView(PostcodeView):
    postcode = None
    uprn = None

    def get(self, request, *args, **kwargs):
        kwargs["postcode"] = self.postcode
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = kwargs
        self.postcode = clean_postcode(kwargs["postcode"])
        self.uprn = self.kwargs.get("uprn")
        context["uprn"] = self.uprn
        context["postcode"] = self.postcode
        self.uprn = self.kwargs.get("uprn")
        context["uprn"] = self.uprn

        context["postelections"] = self.get_ballot_dict()
        context["future_postelections"] = PostcodeView().future_postelections(
            context["postelections"]
        )
        context["show_polling_card"] = True
        context["polling_station"] = self.get_polling_station()
        context[
            "global_registration_card"
        ] = PostcodeView().get_global_registration_card(
            context["postelections"]
        )
        context["registration"] = self.get_registration()
        context["council"] = self.get_electoral_services()
        context[
            "global_postal_vote_card"
        ] = PostcodeView().get_global_postal_vote_card(
            context["postelections"], context["council"]
        )
        context["requires_voter_id"] = "EA-2022"
        context["num_ballots"] = 1
        return context

    def get_ballot_dict(self):
        return [DummyPostElection()]

    def get_electoral_services(self):
        return {
            "council_id": "W06000015",
            "name": "Cardiff Council",
            "nation": "Wales",
            "address": "Electoral Registration Officer\nCity of Cardiff Council\nCounty Hall Atlantic Wharf",
            "postcode": "CF10 4UW",
            "email": "electoralservices@cardiff.gov.uk",
            "phone": "029 2087 2034",
            "website": "http://www.cardiff.gov.uk/",
        }

    def get_registration(self):
        return {
            "address": "Electoral Registration Officer\nCity of Cardiff Council\nCounty Hall Atlantic Wharf",
            "postcode": "CF10 4UW",
            "email": "electoralservices@cardiff.gov.uk",
            "phone": "029 2087 2034",
            "website": "http://www.cardiff.gov.uk/",
        }

    def get_polling_station(self):
        return dummy_polling_station
