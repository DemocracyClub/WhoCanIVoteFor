from django.utils.text import slugify
from elections.tests.factories import ElectionFactoryLazySlug
from people.tests.factories import PersonPostWithPartyFactory


def create_person(
    current=True,
    deceased=False,
    party_name=None,
    election_type="local",
    election_name=None,
    **kwargs,
):
    election_date = "2021-05-06" if current else "2019-12-12"
    death_date = "2021-04-01" if deceased else None
    party_name = party_name or "Test Party"
    party_id = slugify(party_name)
    if party_name == "Independent":
        party_id = "ynmp-party:2"
    election = ElectionFactoryLazySlug(
        name=election_name or "Sheffield local election",
        election_date=election_date,
        current=current,
    )

    return PersonPostWithPartyFactory(
        election=election,
        person__name="Joe Bloggs",
        post__label="Ecclesall",
        post_election__election=election,
        person__death_date=death_date,
        party__party_name=party_name,
        party__party_id=party_id,
        post_election__ballot_paper_id=f"{election_type}.{election.slug}",
        **kwargs,
    )
