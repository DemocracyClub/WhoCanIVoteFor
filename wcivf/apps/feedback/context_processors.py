from .forms import FeedbackForm, NoElectionFeedbackForm


def feedback_form(request):
    return {
        "feedback_form": FeedbackForm(initial={"source_url": request.path}),
        "no_election_feedback_form": NoElectionFeedbackForm(
            initial={"source_url": request.path}
        ),
    }
