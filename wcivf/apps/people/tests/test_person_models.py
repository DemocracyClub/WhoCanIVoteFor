from people.tests.helpers import create_person
from people.tests.factories import PersonFactory
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

    def test_intro_template(self):
        candidacies = [
            # independent
            (
                create_person(party_name="Independent"),
                "people/includes/intros/_independent.html",
            ),
            # mayor
            (
                create_person(election_type="mayor"),
                "people/includes/intros/_mayor.html",
            ),
            # pcc
            (
                create_person(election_type="pcc"),
                "people/includes/intros/_pcc.html",
            ),
            # parl
            (
                create_person(election_type="parl"),
                "people/includes/intros/_parl.html",
            ),
            # speaker
            (
                create_person(party_name="Speaker seeking re-election"),
                "people/includes/intros/_speaker.html",
            ),
            # base
            (
                create_person(election_type="local"),
                "people/includes/intros/base.html",
            ),
            (
                create_person(election_type="sp"),
                "people/includes/intros/base.html",
            ),
            (
                create_person(election_type="senedd"),
                "people/includes/intros/base.html",
            ),
            (
                create_person(election_type="europarl"),
                "people/includes/intros/base.html",
            ),
            (
                create_person(election_type="nia"),
                "people/includes/intros/base.html",
            ),
            (
                create_person(election_type="naw"),
                "people/includes/intros/base.html",
            ),
            # constituency
            (
                create_person(election_type="sp.c"),
                "people/includes/intros/_constituency.html",
            ),
            (
                create_person(election_type="senedd.c"),
                "people/includes/intros/_constituency.html",
            ),
            (
                create_person(election_type="gla.c"),
                "people/includes/intros/_constituency.html",
            ),
            # list,
            (
                create_person(list_election=True),
                "people/includes/intros/_list_ballot.html",
            ),
        ]
        for candidacy in candidacies:
            person = candidacy[0].person
            expected = candidacy[1]
            with self.subTest(msg=candidacy[1]):
                self.assertEqual(person.intro_template, expected)
