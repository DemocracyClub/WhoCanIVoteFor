from django.apps import apps
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, RedirectView, TemplateView
from elections.filters import ElectionTypeFilter
from elections.models import PostElection
from elections.views.mixins import (
    NewSlugsRedirectMixin,
    PostelectionsToPeopleMixin,
)
from parties.models import LocalParty, NationalParty, Party
from people.models import PersonPost


class ElectionsView(TemplateView):
    template_name = "elections/elections_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Election = apps.get_model("elections.Election")
        qs = Election.objects.all().order_by(
            "-election_date", "-election_type", "name"
        )
        f = ElectionTypeFilter(self.request.GET, queryset=qs)
        context["filter"] = f
        context["queryset"] = f.qs

        return context


class ElectionView(NewSlugsRedirectMixin, DetailView):
    template_name = "elections/election_view.html"
    model = apps.get_model("elections.Election")
    pk_url_kwarg = "election"

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        pk = self.kwargs.get(self.pk_url_kwarg)
        PostElection = apps.get_model("elections.PostElection")
        queryset = queryset.filter(slug=pk).prefetch_related(
            Prefetch(
                "postelection_set",
                queryset=PostElection.objects.all()
                .select_related("election", "post")
                .order_by("post__label"),
            )
        )
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj


class RedirectPostView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        PostElection = apps.get_model("elections.PostElection")
        post_id = self.kwargs.get("post_id")
        election_id = self.kwargs.get("election_id")
        model = get_object_or_404(
            PostElection, post__ynr_id=post_id, election__slug=election_id
        )
        url = model.get_absolute_url()
        args = self.request.META.get("QUERY_STRING", "")
        if args and self.query_string:
            url = "%s?%s" % (url, args)
        return url


class PostView(NewSlugsRedirectMixin, PostelectionsToPeopleMixin, DetailView):
    model = apps.get_model("elections.PostElection")

    def get_template_names(self):
        """
        Checks if the object is a Referendum
        """
        if self.object.is_referendum:
            return ["referendums/detail.html"]
        return ["elections/post_view.html"]

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        queryset = queryset.filter(
            ballot_paper_id=self.kwargs["election"]
        ).select_related("post", "election")

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["election"] = self.object.election
        self.object.people = self.people_for_ballot(self.object)
        return context


class PartyListVew(TemplateView):
    template_name = "elections/party_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ballot"] = get_object_or_404(
            PostElection, ballot_paper_id=self.kwargs["election"]
        )

        context["party"] = get_object_or_404(
            Party, party_id=self.kwargs["party_id"]
        )

        local_party_qs = LocalParty.objects.select_related("parent").filter(
            post_election=context["ballot"], parent=context["party"]
        )

        national_party_qs = NationalParty.objects.select_related(
            "parent"
        ).filter(post_election=context["ballot"], parent=context["party"])

        context["party_name"] = context["party"].party_name
        if local_party_qs.exists():
            context["local_party"] = local_party_qs.get()
            context["party_name"] = context["local_party"].name
        if national_party_qs.exists():
            context["national_party"] = national_party_qs.get()
            context["party_name"] = context["national_party"].name

        manifestos = context["party"].manifesto_set.filter(
            election=context["ballot"].election
        )
        if manifestos.exists():
            context["manifesto"] = manifestos.get()

        context["person_posts"] = PersonPost.objects.filter(
            party=context["party"], post_election=context["ballot"]
        ).order_by("list_position")
        return context
