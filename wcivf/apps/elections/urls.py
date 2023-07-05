from django.urls import re_path

from elections.views.postcode_view import DummyPostcodeView

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
from core.views import TranslatedTemplateView

urlpatterns = [
    re_path(r"^$", ElectionsView.as_view(), name="elections_view"),
    re_path(
        r"^(?P<election_id>[a-z0-9\.\-]+)/post-(?P<post_id>.*)/(?P<ignored_slug>[^/]+)$",
        RedirectPostView.as_view(),
        name="redirect_post_view",
    ),
    re_path(
        r"^(?P<election>[201[05]+)/(?P<ignored_slug>[^/]+)/$",
        ElectionView.as_view(),
        name="redirect_election_view",
    ),
    re_path(
        r"^(?P<election>[a-z\-]+\.[^/]+)/(?P<party_id>(joint-party|party|minor-party|ynmp-party):[0-9\-]+)/$",
        PartyListVew.as_view(),
        name="party_list_view",
    ),
    #
    re_path(
        "^(?P<election>[a-z\-]+\.[^/]+)(?:/(?P<ignored_slug>[^/]+))?/$",
        ElectionIDSwitcher(election_view=ElectionView, ballot_view=PostView),
        name="election_view",
    ),
    re_path(
        r"^TE1 1ST/$",
        DummyPostcodeView.as_view(postcode="TE1 1ST"),
        name="dummy_postcode_view",
    ),
    re_path(
        r"^voting_system/fptp/",
        TranslatedTemplateView.as_view(
            template_name="elections/fptp.html",
            extra_context={"voting_system": "First-past-the-post"},
        ),
        name="fptp_voting_system_view",
    ),
    re_path(
        r"^voting_system/ams/",
        TranslatedTemplateView.as_view(
            template_name="elections/ams.html",
            extra_context={"voting_sytem": "Additional Member System"},
        ),
        name="ams_voting_system_view",
    ),
    re_path(
        r"^voting_system/sv/",
        TranslatedTemplateView.as_view(
            template_name="elections/sv.html",
            extra_context={"voting_sytem": "Supplementary Vote"},
        ),
        name="sv_voting_system_view",
    ),
    re_path(
        r"^voting_system/STV/",
        TranslatedTemplateView.as_view(
            template_name="elections/stv.html",
            extra_context={"voting_sytem": "Single Transferable Vote"},
        ),
        name="stv_voting_system_view",
    ),
    re_path(
        r"^(?P<postcode>[^/]+)/(?P<uprn>[^/]+)/$",
        PostcodeView.as_view(),
        name="uprn_view",
    ),
    re_path(
        r"^(?P<postcode>[^/]+).ics$",
        PostcodeiCalView.as_view(),
        name="postcode_ical_view",
    ),
    re_path(
        r"^(?P<postcode>[^/]+)/(?P<uprn>[^/]+).ics$",
        PostcodeiCalView.as_view(),
        name="uprn_ical_view",
    ),
    re_path(
        r"^(?P<postcode>[^/]+)/$", PostcodeView.as_view(), name="postcode_view"
    ),
]
