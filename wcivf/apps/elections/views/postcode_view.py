from icalendar import Calendar, Event, vText

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView, View

from core.helpers import clean_postcode
from .mixins import (
    LogLookUpMixin,
    PostcodeToPostsMixin,
    PollingStationInfoMixin,
    PostelectionsToPeopleMixin,
    NewSlugsRedirectMixin,
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.postcode = clean_postcode(kwargs["postcode"])
        context["postcode"] = self.postcode
        self.log_postcode(context["postcode"])
        context["postelections"] = self.postcode_to_ballots(context["postcode"])

        context["voter_id_required"] = [
            (pe, pe.election.metadata.get("2019-05-02-id-pilot"))
            for pe in context["postelections"]
            if pe.election.metadata
            and pe.election.metadata.get("2019-05-02-id-pilot")
        ]
        context["people_for_post"] = {}
        for postelection in context["postelections"]:
            postelection.people = self.people_for_ballot(postelection)

        context["polling_station"] = self.get_polling_station_info(
            context["postcode"]
        )

        return context


class PostcodeiCalView(
    NewSlugsRedirectMixin, PostcodeToPostsMixin, View, PollingStationInfoMixin
):

    pk_url_kwarg = "postcode"

    def get(self, request, *args, **kwargs):
        postcode = kwargs["postcode"]
        polling_station = self.get_polling_station_info(postcode)

        cal = Calendar()
        cal["summary"] = "Elections in {}".format(postcode)
        cal["X-WR-CALNAME"] = "Elections in {}".format(postcode)
        cal["X-WR-TIMEZONE"] = "Europe/London"

        cal.add("version", "2.0")
        cal.add("prodid", "-//Elections in {}//mxm.dk//".format(postcode))

        for post_election in self.postcode_to_ballots(postcode):
            event = Event()
            event["uid"] = "{}-{}".format(
                post_election.post.ynr_id, post_election.election.slug
            )
            event["summary"] = "{} - {}".format(
                post_election.election.name, post_election.post.label
            )

            event.add("dtstart", post_election.election.start_time)
            event.add("dtend", post_election.election.end_time)
            event.add(
                "DESCRIPTION",
                "Find out more at {}/elections/{}/".format(
                    settings.CANONICAL_URL, postcode.replace(" ", "")
                ),
            )
            if polling_station.get("polling_station_known"):
                geometry = polling_station["polling_station"]["geometry"]
                if geometry:
                    event["geo"] = "{};{}".format(
                        geometry["coordinates"][0], geometry["coordinates"][1]
                    )
                properties = polling_station["polling_station"]["properties"]
                event["location"] = vText(
                    "{}, {}".format(
                        properties["address"].replace("\n", ", "),
                        properties["postcode"],
                    )
                )

            cal.add_component(event)

        return HttpResponse(cal.to_ical(), content_type="text/calendar")
