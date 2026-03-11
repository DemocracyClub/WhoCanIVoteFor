from core.slack import SlackHelper
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView
from elections.models import PostElection
from hustings.forms import AddHustingForm
from hustings.models import Husting


class AddHustingView(CreateView):
    model = Husting
    form_class = AddHustingForm

    def get_initial(self):
        ret = super().get_initial()
        self.ballot = get_object_or_404(
            PostElection, **{"ballot_paper_id": self.kwargs["ballot_paper_id"]}
        )
        ret["post_election"] = self.ballot.pk
        print("called")
        return ret

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["post_election"].initial = self.ballot.pk
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ballot"] = self.ballot
        return context

    def form_valid(self, form):
        form.instance.post_election = self.ballot
        messages.success(
            self.request,
            "Thanks for telling us about this husting. The team will review it.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        # Post to Slack in this method as we know that the data has
        # been saved at this point. If Slack fails for some reason, we'll give
        # the user a 500, but their data will not be lost
        self.post_to_slack()
        return self.ballot.get_absolute_url()

    def post_to_slack(self):
        hust: Husting = self.object
        slack_helper = SlackHelper()
        slack_helper.post_message(
            # DC Slack Hustings channel
            getattr(settings, "SLACK_HUSTINGS_CHANNEL", "C53KNT7NH"),
            "New hustings added",
            blocks=hust.as_slack_blocks(),
            extra_dict={"icon_emoji": ":calendar:"},
        )
