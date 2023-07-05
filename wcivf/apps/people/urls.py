from django.urls import re_path, path

from .views import PersonView, EmailPersonView, DummyPersonView

urlpatterns = [
    path(
        "dummy-profile/<slug:name>/",
        DummyPersonView.as_view(),
        name="dummy-profile",
    ),
    re_path(
        r"^(?P<pk>[^/]+)/email/(?P<ignored_slug>.*)$",
        EmailPersonView.as_view(),
        name="email_person_view",
    ),
    path(
        "<int:pk>/<slug:ignored_slug>",
        PersonView.as_view(),
        name="person_view",
    ),
]
