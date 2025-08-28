from django.urls import re_path

from .views import (
    FeedbackFormView,
    NoElectionFeedbackFormView,
    RecordJsonFeedback,
)

urlpatterns = [
    re_path(
        r"^submit_initial",
        RecordJsonFeedback.as_view(),
        name="json_feedback_view",
    ),
    re_path(r"^$", FeedbackFormView.as_view(), name="feedback_form_view"),
    re_path(
        r"^no_election$",
        NoElectionFeedbackFormView.as_view(),
        name="no_election_feedback_form_view",
    ),
]
