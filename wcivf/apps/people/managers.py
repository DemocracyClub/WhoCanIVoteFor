from copy import deepcopy

from django.db import models
from django.db.models import Count

from elections.models import Election, Post
from parties.models import Party


class PersonPostQuerySet(models.QuerySet):
    def by_party(self):
        return self.order_by('party__party_name', 'list_position')

    def elected(self):
        return self.filter(elected=True)

    def counts_by_post(self):
        return self.values(
            'post__label', 'post_id', 'election__slug', 'election__name')\
            .annotate(num_candidates=Count('person'))\
            .order_by('-election__election_date', 'post__label',)


class PersonPostManager(models.Manager):
    def get_queryset(self):
        return PersonPostQuerySet(self.model, using=self._db)

    def by_party(self):
        return self.get_queryset().by_party()

    def elected(self):
        return self.get_queryset().elected()

    def counts_by_post(self):
        return self.get_queryset().counts_by_post()


class PersonManager(models.Manager):

    def update_or_create_from_ynr(self, person,
                                  all_elections=None,
                                  all_posts=None,
                                  all_parties=None):
        posts = []
        elections = []

        defaults = {
            'name': person['name'],
            'email': person['email'] or None,
            'gender': person['gender'] or None,
            'birth_date': person['birth_date'] or None,
        }

        version_data = person['versions'][0]['data']
        if 'twitter_username' in version_data:
            defaults['twitter_username'] = version_data['twitter_username']
        if 'facebook_page_url' in version_data:
            defaults['facebook_page_url'] = version_data['facebook_page_url']
        if 'facebook_personal_url' in version_data:
            defaults['facebook_personal_url'] = \
                version_data['facebook_personal_url']
        if 'linkedin_url' in version_data:
            defaults['linkedin_url'] = version_data['linkedin_url']
        if 'homepage_url' in version_data:
            defaults['homepage_url'] = version_data['homepage_url']
        if 'wikipedia_url' in version_data:
            defaults['wikipedia_url'] = version_data['wikipedia_url']
        if 'biography' in version_data:
            defaults['statement_to_voters'] = version_data['biography']
        if 'thumbnail' in person:
            defaults['photo_url'] = person['thumbnail']
        if 'extra_fields' in version_data \
                and 'favourite_biscuits' in version_data['extra_fields']:
            defaults['favourite_biscuit'] = \
                version_data['extra_fields']['favourite_biscuits']
        if 'identifiers' in version_data:
            for i in version_data['identifiers']:
                if i['scheme'] == 'uk.org.publicwhip':
                    defaults['twfy_id'] = i['identifier'].replace(
                        "uk.org.publicwhip/person/", "")

        if person['memberships']:
            for membership in person['memberships']:
                election = None
                post = None

                if membership['election']:
                    election_slug = membership['election']['id']
                    try:
                        election = all_elections[election_slug]
                    except KeyError:
                        election = Election.objects.get(slug=election_slug)
                    elections.append(election)

                if membership['post']:
                    post_id = membership['post']['id']
                    try:
                        post = all_posts[post_id]
                    except KeyError:
                        post = Post.objects.get(ynr_id=post_id)
                    if election:
                        post.election = election

                post.party_list_position = membership['party_list_position']

                if membership['on_behalf_of']:
                    post.party_id = membership['on_behalf_of']['id']
                else:
                    post.party_id = None
                # If the same post occurs twice (e.g. if the candidate has
                # stood twice as an MP in the same seat), make
                # sure we have the correct election/party information for
                # each post, by taking a deep copy.
                post_copy = deepcopy(post)
                posts.append(post_copy)

        person_id = person['id']
        person_obj, _ = self.update_or_create(
            ynr_id=person['id'],
            defaults=defaults
        )

        if posts:
            from .models import PersonPost
            # Delete old posts for this person
            PersonPost.objects.filter(person_id=person_id).delete()
            # import ipdb; ipdb.set_trace()
            for post in posts:
                defaults = {
                    'list_position': post.party_list_position
                }
                if post.party_id:
                    try:
                        defaults['party'] = all_parties[post.party_id]
                    except KeyError:
                        defaults['party'] = Party.objects.get(
                            party_id=post.party_id)
                PersonPost.objects.update_or_create(
                    post=post,
                    election=post.election,
                    person_id=person_id,
                    defaults=defaults
                )

        return person_obj
