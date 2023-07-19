from django.urls import reverse
from django.views.generic import DetailView, RedirectView
from django.http import Http404
from django.db.models import Prefetch, Q, Count

from elections.dummy_models import DummyPostElection

from .models import Person, PersonPost
from parties.models import Manifesto


class PersonMixin(object):
    def get_object(self, queryset=None):
        return self.get_person(queryset)

    def get_person(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        pk = self.kwargs.get(self.pk_url_kwarg)
        queryset = (
            queryset.filter(ynr_id=pk)
            .select_related("cv")
            .prefetch_related(
                Prefetch(
                    "personpost_set",
                    queryset=PersonPost.objects.all()
                    .select_related(
                        "election", "post", "party", "post_election"
                    )
                    .prefetch_related(
                        "previous_party_affiliations",
                    ),
                ),
                "facebookadvert_set",
                # "leaflet_set",
            )
        )
        queryset = queryset.annotate(
            previous_party_count=Count(
                "personpost__previous_party_affiliations"
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

        # TODO check if this can be deleted or may be needed in future?
        # obj.leaflets = Leaflet.objects.filter(person=obj).order_by(
        #     "-date_uploaded_to_electionleaflets"
        # )[:3]

        return obj


class PersonView(DetailView, PersonMixin):
    model = Person

    def get_template_names(self):
        """
        When we don't have a TheyWorkForYou ID or the person has no current
        candidacies, we return an alternative template with just intro and past
        elections.
        """
        if self.object.twfy_id or self.object.current_or_future_candidacies:
            return ["people/person_detail.html"]
        return ["people/not_current_person_detail.html"]

    def get_object(self, queryset=None):
        obj = self.get_person(queryset)
        obj.title = self.get_title(obj)
        obj.post_country = self.get_post_country(obj)

        if obj.featured_candidacy:
            # We can't show manifestos if they've never stood for a party
            obj.manifestos = Manifesto.objects.filter(
                party=obj.featured_candidacy.party,
                election=obj.featured_candidacy.election,
            ).filter(
                Q(country="Local")
                | Q(country="UK")
                | Q(country=obj.post_country)
            )
            obj.manifestos = sorted(
                obj.manifestos, key=lambda n: n.country != "UK"
            )

            obj.local_party = (
                obj.featured_candidacy.post_election.localparty_set.filter(
                    parent=obj.featured_candidacy.party
                ).first()
            )

        return obj

    def get_post_country(self, person):
        country = None
        if person.featured_candidacy:
            post_id = person.featured_candidacy.post_id
            # Hack to get candidate's country.
            if post_id.startswith("gss:") or post_id.startswith("WMC:"):
                id = post_id.split(":")[1]
                if id.startswith("E"):
                    country = "England"
                elif id.startswith("W"):
                    country = "Wales"
                elif id.startswith("S"):
                    country = "Scotland"
                elif id.startswith("N"):
                    country = "Northern Ireland"
        return country

    def get_title(self, person):
        title = person.name
        if person.featured_candidacy:
            title += " for " + person.featured_candidacy.post.label + " in the "
            title += person.featured_candidacy.election.name
        return title


class DummyPersonView(PersonView):
    def get_template_names(self):
        return ["people/person_detail.html"]

    def get_object(self):
        candidate = self.candidates().get(self.kwargs["name"])
        if not candidate:
            raise Http404()
        return candidate.person

    def candidates(self):
        return {
            candidate.person.name_slug: candidate
            for candidate in DummyPostElection().people()
        }


class EmailPersonView(RedirectView):
    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        return reverse("person_view", kwargs={"pk": self.kwargs["pk"]})
