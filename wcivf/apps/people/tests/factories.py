import factory

from people.models import Person, PersonPost
from elections.tests.factories import ElectionFactory, PostFactory


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person

    ynr_id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: "Candidate %d" % n)
    elections = factory.RelatedFactory(ElectionFactory)


class PersonPostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PersonPost

    person = factory.SubFactory(PersonFactory)
    post = factory.SubFactory(PostFactory)
    party = None
    list_position = None
