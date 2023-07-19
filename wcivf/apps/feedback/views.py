from django.utils import timezone
from django.http import HttpResponse
from django.views.generic import View, UpdateView
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.template.loader import render_to_string
from akismet import Akismet
from django.conf import settings

from .forms import FeedbackForm
from .models import Feedback


class FeedbackFormView(UpdateView):
    form_class = FeedbackForm
    template_name = "feedback/feedback_form_view.html"

    @property
    def is_spam(self):
        if not settings.AKISMET_API_KEY:
            return False

        akismet = Akismet(
            settings.AKISMET_API_KEY, blog=settings.AKISMET_BLOG_URL
        )
        return akismet.check(
            self.request.META["REMOTE_ADDR"],
            comment_content=self.request.POST.get("comments"),
        )

    def get_object(self, queryset=None):
        token = self.request.POST.get("token")
        try:
            return Feedback.objects.get(
                token=token, created__date=timezone.datetime.today()
            )
        except Feedback.DoesNotExist:
            if token:
                return Feedback(token=token)
            return Feedback()

    def get_success_url(self):
        messages.success(
            self.request,
            render_to_string(
                "feedback/feedback_thanks.html",
                request=self.request,
                context={"object": self.object},
            ),
            extra_tags="template",
        )

        if url_has_allowed_host_and_scheme(
            self.object.source_url, allowed_hosts=None
        ):
            return self.object.source_url
        else:
            return "/"

    def form_valid(self, form):
        if self.is_spam:
            self.object.flagged_as_spam = True
        return super().form_valid(form)


class RecordJsonFeedback(View):
    def post(self, request):
        found_useful = request.POST.get("found_useful")
        source_url = request.POST.get("source_url")
        token = request.POST.get("token")
        Feedback.objects.update_or_create(
            token=token,
            defaults={"found_useful": found_useful, "source_url": source_url},
        )
        return HttpResponse()
