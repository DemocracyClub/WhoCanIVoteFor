import datetime
import os

from django import http
from django.conf import settings
from django.urls import reverse
from django.utils import timezone, translation
from django.views.generic import FormView, TemplateView, View

from .forms import PostcodeLookupForm


class TranslatedTemplateView(TemplateView):
    def get_template_names(self):
        templates = super().get_template_names()
        base_template_name, ext = self.template_name.rsplit(".", 1)
        current_language = translation.get_language()
        if current_language != "en":
            templates.insert(
                0, f"{base_template_name}_{current_language}.{ext}"
            )
        return templates


class PostcodeFormView(FormView):
    form_class = PostcodeLookupForm

    def get(self, request, *args, **kwargs):
        if (
            request.GET.get("postcode")
            and "invalid_postcode" not in self.request.GET
        ):
            redirect_url = reverse(
                "postcode_view", kwargs={"postcode": request.GET["postcode"]}
            )
            return http.HttpResponseRedirect(redirect_url)
        return super(PostcodeFormView, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = self.initial.copy()
        if "invalid_postcode" in self.request.GET:
            initial["postcode"] = self.request.GET.get("postcode")
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"autofocus": True})
        return kwargs

    def form_invalid(self, form):
        data = self.request.GET.copy()
        data.update({"invalid_postcode": 1, "postcode": form.data["postcode"]})
        self.request.GET = data
        return super().form_invalid(form)

    def form_valid(self, form):
        postcode = form.cleaned_data["postcode"]
        self.success_url = reverse(
            "postcode_view", kwargs={"postcode": postcode}
        )
        return super().form_valid(form)


class HomePageView(PostcodeFormView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Comment in this code to hide upcoming elections on the homepage
        context["upcoming_elections"] = None

        # Comment in this code to show upcoming elections on the homepage
        # today = datetime.datetime.today()
        # delta = datetime.timedelta(weeks=4)
        # cut_off_date = today + delta
        # context["upcoming_elections"] = (
        #     PostElection.objects.filter(
        #         election__election_date__gte=today,
        #         election__election_date__lte=cut_off_date,
        #         # Temporarily removed following May elections #
        #         election__any_non_by_elections=False,
        #     )
        #     .exclude(election__election_date=may_election_day_this_year())
        #     .select_related("election", "post")
        #     .order_by("election__election_date")
        # )
        polls_open = timezone.make_aware(
            datetime.datetime.strptime("2019-12-12 7", "%Y-%m-%d %H")
        )
        polls_close = timezone.make_aware(
            datetime.datetime.strptime("2019-12-12 22", "%Y-%m-%d %H")
        )
        now = timezone.now()

        context["show_polls_open"] = polls_close > now
        context["poll_date"] = "on Thursday 12 December"
        if polls_open < now and polls_close > now:
            context["poll_date"] = "today"
        context["show_gb_id_messaging"] = getattr(
            settings, "SHOW_GB_ID_MESSAGING", False
        )
        context["show_results_chart"] = getattr(
            settings, "SHOW_RESULTS_CHART", False
        )

        return context


class OpenSearchView(TemplateView):
    template_name = "opensearch.xml"
    content_type = "text/xml"

    def get_context_data(self, **kwargs):
        context = super(OpenSearchView, self).get_context_data(**kwargs)
        context["CANONICAL_URL"] = settings.CANONICAL_URL
        context["SITE_TITLE"] = settings.SITE_TITLE
        return context


class StatusCheckView(View):
    @property
    def server_is_dirty(self):
        if getattr(settings, "CHECK_HOST_DIRTY", False):
            dirty_file_path = os.path.expanduser(
                getattr(settings, "DIRTY_FILE_PATH")
            )

            if os.path.exists(dirty_file_path):
                return True
        return False

    def get(self, request, *args, **kwargs):
        status = 503

        data = {"ready_to_serve": False}

        if not self.server_is_dirty:
            status = 200
            data["ready_to_serve"] = True

        return http.JsonResponse(data, status=status)
