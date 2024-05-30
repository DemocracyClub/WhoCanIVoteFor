import factory
from elections.tests.factories import PostElectionFactory
from parties.models import LocalParty, NationalParty, Party


class PartyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Party
        django_get_or_create = ("party_id",)

    party_id = "PP01"
    party_name = "Test Party"


class LocalPartyFactory(factory.django.DjangoModelFactory):
    parent = factory.SubFactory(PartyFactory)
    post_election = factory.SubFactory(PostElectionFactory)

    class Meta:
        model = LocalParty


class NationalPartyFactory(factory.django.DjangoModelFactory):
    parent = factory.SubFactory(PartyFactory)
    post_election = factory.SubFactory(PostElectionFactory)

    class Meta:
        model = NationalParty
