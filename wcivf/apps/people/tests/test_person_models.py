from elections.tests.factories import (
    ElectionFactory,
)
from parties.tests.factories import PartyFactory
from people.tests.factories import PersonFactory, PersonPostFactory
from django.test import TestCase


class TestPersonModel(TestCase):
    def setUp(self):
        self.person = PersonFactory()

    def test_long_statement(self):
        self.person.statement_to_voters = "Lorem ipsum dolor sit amet, yo consectetur adipiscing elit. Nam eget metus dui. Integer a velit viverra, interdum dui eget, lobortis massa. Nam pharetra, risus eu gravida ullamcorper, enim nisl ornare lectus, at eleifend tellus lacus quis velit. Sed ornare volutpat aliquam. Donec fermentum dapibus odio, vel gravida augue ornare non. Donec ultrices consequat ullamcorper. Proin ac ante et tellus ultrices aliquam lobortis quis orci. Nunc eget eros facilisis, sagittis nibh quis, feugiat purus. Integer nibh erat, dapibus eget vehicula non, tincidunt at eros. Etiam varius ultricies mollis. Morbi eros diam, hendrerit eu condimentum maximus, lobortis sit amet turpis. Cras quam."
        assert self.person.long_statement is True

    def test_short_statement(self):
        self.person.statement_to_voters = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing eight"
        )
        assert self.person.long_statement is False

    def test_statement_count(self):
        self.person.statement_to_voters = "Lorem ipsum dolor sit amet"
        assert self.person.statement_count == 5

    def test_statement_intro(self):
        self.person.statement_to_voters = "Lorem ipsum dolor sit amet.\nConsectetur adipiscing elit.\nVivamus est eleven."
        assert self.person.statement_intro == "Lorem ipsum dolor sit amet."

    def test_statement_remainder(self):
        self.person.statement_to_voters = "Lorem ipsum dolor sit amet. Consectetur adipiscing elit. Vivamus est eleven."
        assert (
            self.person.statement_remainder
            == " Consectetur adipiscing elit. Vivamus est eleven."
        )

    def test_display_deceased(self):
        self.party = PartyFactory()
        self.election = ElectionFactory()
        self.personpost = PersonPostFactory(
            person=self.person, party=self.party, election=self.election
        )
        self.person.death_date = "01/01/2021"
        assert self.person.display_deceased is True

    def test_facebook_personal_username(self):
        self.person.facebook_personal_url = (
            "https://www.facebook.com/vicky.ford.142"
        )
        assert self.person.facebook_personal_username == "vicky.ford.142"

    def test_facebook_username(self):
        self.person.facebook_page_url = (
            "https://www.facebook.com/vicky4chelmsford"
        )
        assert self.person.facebook_username == "vicky4chelmsford"

    def test_instagram_username(self):
        self.person.instagram_url = "https://www.instagram.com/vickyfordmp"
        assert self.person.instagram_username == "vickyfordmp"

    def test_linkedin_username(self):
        self.person.linkedin_url = "https://www.linkedin.com/in/vicky-ford/"
        assert self.person.linkedin_username == "vicky-ford"

    def test_youtube_username(self):
        self.person.youtube_profile = (
            "https://www.youtube.com/user/pierscorbyn2"
        )
        assert self.person.youtube_username == "pierscorbyn2"
