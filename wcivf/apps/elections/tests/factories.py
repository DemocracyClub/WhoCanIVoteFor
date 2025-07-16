import factory
from django.utils import timezone
from django.utils.text import slugify
from elections.models import Election, Post, PostElection


class ElectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Election
        django_get_or_create = ("slug",)

    slug = "parl.2015-05-07"
    election_date = timezone.datetime(2015, 5, 7).date()
    current = True
    name = "UK General Election 2015"
    any_non_by_elections = True


class ElectionFactoryLazySlug(ElectionFactory):
    """
    Factory that sets slug 'lazily' to ensure that a new object is always
    created
    """

    @factory.lazy_attribute_sequence
    def slug(self, n):
        """
        Build unique slug. Changes - to . to match election_view
        regex
        """
        slug = slugify(self.name).replace("-", ".")
        return f"{slug}.{n}"


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post
        django_get_or_create = ("ynr_id",)

    ynr_id = "WMC:E14000647"
    label = "copeland"
    organization_type = "local-authority"
    territory = "ENG"


class PostElectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PostElection
        django_get_or_create = ("post", "election")

    post = factory.SubFactory(PostFactory)
    election = factory.SubFactory(ElectionFactory)
    winner_count = 1
    ballot_paper_id = factory.Sequence(
        lambda n: "parl.place-name-%d.2015-05-07" % n
    )


class ElectionWithPostFactory(ElectionFactoryLazySlug):
    """
    Builds an Election with a related Post through a PostElection
    """

    ballot = factory.RelatedFactory(
        PostElectionFactory, factory_related_name="election"
    )
