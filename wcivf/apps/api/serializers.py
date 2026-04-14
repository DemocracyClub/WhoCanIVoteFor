from elections.models import VotingSystem
from leaflets.api.serializers import LeafletSerializer
from parties.models import Party
from people.models import Person, PersonPost
from rest_framework import serializers


class PersonSerializer(serializers.ModelSerializer):
    absolute_url = serializers.SerializerMethodField()

    def get_absolute_url(self, obj):
        if "request" in self.context:
            return self.context["request"].build_absolute_uri(
                obj.get_absolute_url()
            )
        return obj.get_absolute_url()

    class Meta:
        model = Person
        fields = (
            "ynr_id",
            "name",
            "absolute_url",
            "email",
            "photo_url",
            "leaflets",
        )

    leaflets = serializers.SerializerMethodField(allow_null=True)

    def get_leaflets(self, obj: Person):
        leaflets = obj.ordered_leaflets[:4]
        if leaflets:
            return LeafletSerializer(leaflets, many=True, read_only=True).data
        return None


class PartySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Party
        fields = ("party_id", "party_name")


class PersonPostSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PersonPost
        fields = (
            "list_position",
            "party",
            "person",
            "previous_party_affiliations",
        )

    person = PersonSerializer(many=False, read_only=True)
    party = PartySerializer(many=False, read_only=True)
    list_position = serializers.SerializerMethodField(allow_null=True)
    previous_party_affiliations = serializers.SerializerMethodField(
        allow_null=True
    )

    def get_list_position(self, obj):
        """
        Needed because YNR's data model allows adding party list positions
        to ballots that don't use them. Should fix there, but this is for quick
        wins

        """

        if pe := self.context.get("postelection"):
            post_election = pe
        else:
            post_election = obj.post_election
        if post_election.display_as_party_list:
            return obj.list_position
        return None

    def get_previous_party_affiliations(self, obj: PersonPost):
        parties = obj.previous_party_affiliations.all()
        if parties:
            return PartySerializer(parties, many=True, read_only=True).data
        return None


class VotingSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = VotingSystem
        fields = ("slug", "name", "uses_party_lists")
