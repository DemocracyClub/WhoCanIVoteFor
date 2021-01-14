from django.views.generic import DetailView
from django.http import Http404
from django.db.models import Prefetch, Q
from django.utils.html import strip_tags
from django.contrib.humanize.templatetags.humanize import intcomma

from .models import Person, PersonPost
from elections.models import PostElection
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
                    queryset=PersonPost.objects.all().select_related(
                        "election", "post", "party", "post_election"
                    ),
                ),
                "facebookadvert_set",
                # "leaflet_set",
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

    def get_object(self, queryset=None):
        obj = self.get_person(queryset)

        obj.personpost = None
        if obj.current_or_future_candidacies:
            obj.personpost = obj.current_or_future_candidacies.first()
        elif obj.past_not_current_candidacies:
            obj.personpost = obj.past_not_current_candidacies.first()
        obj.postelection = None
        if obj.personpost:
            try:
                obj.postelection = PostElection.objects.get(
                    post=obj.personpost.post, election=obj.personpost.election
                )
            except PostElection.DoesNotExist:
                pass
        obj.title = self.get_title(obj)
        obj.intro = self.get_intro(obj)
        obj.text_intro = strip_tags(obj.intro)
        obj.post_country = self.get_post_country(obj)

        if obj.personpost:
            # We can't show manifestos if they've never stood for a party
            obj.manifestos = Manifesto.objects.filter(
                party=obj.personpost.party, election=obj.personpost.election
            ).filter(
                Q(country="Local")
                | Q(country="UK")
                | Q(country=obj.post_country)
            )
            obj.manifestos = sorted(
                obj.manifestos, key=lambda n: n.country != "UK"
            )

            obj.local_party = (
                obj.personpost.post_election.localparty_set.filter(
                    parent=obj.personpost.party
                ).first()
            )

        return obj

    def get_post_country(self, person):
        country = None
        if person.personpost:
            post_id = person.personpost.post_id
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
        if person.personpost:
            title += " for " + person.personpost.post.label + " in the "
            title += person.personpost.election.name
        return title

    def get_intro(self, person):
        intro = [person.name]

        if person.current_or_future_candidacies and not person.death_date:
            intro.append("is")
        else:
            intro.append("was")

        if person.personpost:
            party = person.personpost.party
            if party:
                if party.party_name == "Independent":
                    intro.append("an independent candidate")
                elif party.party_name == "Speaker seeking re-election":
                    intro.append("the Speaker seeking re-election")
                else:
                    intro.append("the")
                    str = '<a href="' + party.get_absolute_url() + '">'
                    str += party.party_name + "</a> candidate"
                    intro.append(str)
            else:
                intro.append("a candidate")
            intro.append("in")
            if (
                person.personpost.post.organization
                == "House of Commons of the United Kingdom"
            ):
                intro.append("the constituency of")
            if person.postelection:
                str = '<a href="' + person.postelection.get_absolute_url()
                str += '">' + person.personpost.post.label + "</a>"
            else:
                str = person.personpost.post.label
            str += ' in the <a href="'
            str += person.personpost.election.get_absolute_url()
            str += '">' + person.personpost.election.name + "</a>"
            intro.append(str)

            if person.personpost.votes_cast:
                votes = intcomma(person.personpost.votes_cast)
                if person.personpost.elected:
                    intro[-1] = intro[-1] + "."
                    results_str = (
                        "They were elected with <strong>{}</strong> votes"
                    )
                else:
                    results_str = ". They got <strong>{}</strong> votes"
                results_str = results_str.format(votes)
                intro.append(results_str)

        return " ".join(intro)


class EmailPersonView(PersonMixin, DetailView):
    template_name = "people/email_person.html"
    model = Person
