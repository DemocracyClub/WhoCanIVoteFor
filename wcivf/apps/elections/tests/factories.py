import factory

from elections.models import Election, Post, PostElection


class ElectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Election
        django_get_or_create = ("slug",)

    slug = "parl.2015"
    election_date = "2015-05-07"
    current = True
    name = "UK General Election 2015"


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post
        django_get_or_create = ("ynr_id",)

    ynr_id = "WMC:E14000647"
    label = "copeland"
    elections = factory.RelatedFactory(ElectionFactory)


class PostElectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PostElection
        django_get_or_create = ("post", "election")

    post = factory.SubFactory(PostFactory)
    election = factory.SubFactory(ElectionFactory)
    ballot_paper_id = factory.Sequence(
        lambda n: "parl.place-name-%d.2015-05-07" % n
    )
