from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    path(
        "",
        RedirectView.as_view(
            url="https://whocanivotefor.co.uk/elections/parl.2024-07-04/uk-parliament-elections/"
        ),
        name="home",
    ),
    path(
        "details/",
        RedirectView.as_view(
            url="https://whocanivotefor.co.uk/elections/parl.2024-07-04/uk-parliament-elections/"
        ),
        name="details",
    ),
]
