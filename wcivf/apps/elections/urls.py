from django.conf.urls import url
from django.views.generic import TemplateView

from .views import (
    PostcodeView,
    ElectionsView,
    ElectionView,
    PostView,
    PostcodeiCalView,
    RedirectPostView,
    PartyListVew,
)
from .helpers import ElectionIDSwitcher

urlpatterns = [
    url(r"^$", ElectionsView.as_view(), name="elections_view"),
    url(
        r"^(?P<election_id>[a-z0-9\.\-]+)/post-(?P<post_id>.*)/(?P<ignored_slug>[^/]+)$",
        RedirectPostView.as_view(),
        name="redirect_post_view",
    ),
    url(
        r"^(?P<election>[201[05]+)/(?P<ignored_slug>[^/]+)/$",
        ElectionView.as_view(),
        name="redirect_election_view",
    ),
    url(
        r"^(?P<election>[a-z\-]+\.[^/]+)/(?P<party_id>(joint-party|party|minor-party|ynmp-party):[0-9\-]+)/$",
        PartyListVew.as_view(),
        name="party_list_view",
    ),
    #
    url(
        "^(?P<election>[a-z\-]+\.[^/]+)(?:/(?P<ignored_slug>[^/]+))?/$",
        ElectionIDSwitcher(election_view=ElectionView, ballot_view=PostView),
        name="election_view",
    ),
    url(
        r"^(?P<postcode>[^/]+)/$", PostcodeView.as_view(), name="postcode_view"
    ),
    url(
        r"^(?P<postcode>[^/]+).ics$",
        PostcodeiCalView.as_view(),
        name="postcode_ical_view",
    ),
    url(
        r"^voting_system/fptp/",
        TemplateView.as_view(template_name="elections/fptp.html"),
        name="fptp_voting_system_view",
    ),
    url(
        r"^voting_system/ams/",
        TemplateView.as_view(template_name="elections/ams.html"),
        name="ams_voting_system_view",
    ),
    url(
        r"^voting_system/sv/",
        TemplateView.as_view(template_name="elections/sv.html"),
        name="sv_voting_system_view",
    ),
]
