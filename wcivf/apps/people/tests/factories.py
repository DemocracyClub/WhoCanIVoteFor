import factory
from elections.tests.factories import (
    ElectionFactory,
    PostElectionFactory,
    PostFactory,
)
from parties.tests.factories import PartyFactory
from people.models import Person, PersonPost


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person
        django_get_or_create = ("ynr_id",)

    ynr_id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: "Candidate %d" % n)
    elections = factory.RelatedFactory(ElectionFactory)


class PersonPostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PersonPost

    person = factory.SubFactory(PersonFactory)
    post = factory.SubFactory(PostFactory)
    post_election = factory.SubFactory(PostElectionFactory)
    party = None
    list_position = None


class PersonPostWithPartyFactory(PersonPostFactory):
    party = factory.SubFactory(PartyFactory)

    @factory.lazy_attribute
    def party_name(self):
        return self.party.party_name
