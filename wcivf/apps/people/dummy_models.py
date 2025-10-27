from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.text import slugify
from elections.models import Post
from people.models import Person, PersonPost


class DummyCandidacy(PersonPost):
    post = Post(label="Made-Up-Ward")

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.person.featured_candidacy = self


class DummyPerson(Person):
    intro_template = "people/includes/intros/base.html"

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statement_to_voters = render_to_string(
            template_name=f"people/dummy_statements/{self.name_slug}.txt"
        )
        self.photo_url = static(f"images/{self.name_slug}.png")
        self.email = f"{self.name_slug}@example.com"
        self.facebook_page_url = "#"
        self.linkedin_url = "#"
        self.homepage_url = f"https://example.com/{self.name_slug}/"
        self.blog_url = f"https://example.com/{self.name_slug}/blog/"
        self.youtube_profile = "#"

    def _is_pk_set(self):
        return True

    @property
    def facebook_username(self):
        return self.name_slug

    @property
    def linkedin_username(self):
        return self.name_slug

    @property
    def youtube_username(self):
        return f"{self.name_slug}-youtube"

    @property
    def name_slug(self):
        return slugify(self.name)

    @property
    def current_or_future_candidacies(self):
        return True

    def get_absolute_url(self):
        return reverse(
            viewname="dummy-profile", kwargs={"name": self.name_slug}
        )
