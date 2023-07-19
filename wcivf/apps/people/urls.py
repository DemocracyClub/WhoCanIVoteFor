from django.urls import path

from .views import PersonView, EmailPersonView, DummyPersonView

urlpatterns = [
    path(
        "dummy-profile/<slug:name>/",
        DummyPersonView.as_view(),
        name="dummy-profile",
    ),
    path(
        "<int:pk>/email/<slug:ignored_slug>",
        EmailPersonView.as_view(),
        name="email_person_view",
    ),
    path(
        "<int:pk>/<slug:ignored_slug>",
        PersonView.as_view(),
        name="person_view",
    ),
    path(
        "<int:pk>",
        PersonView.as_view(),
        name="person_view",
    ),
]
