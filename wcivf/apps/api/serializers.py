from rest_framework import serializers

from people.models import Person, PersonPost
from parties.models import Party


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
        fields = ("ynr_id", "name", "absolute_url", "email", "photo_url")


class PartySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Party
        fields = ("party_id", "party_name")


class PersonPostSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PersonPost
        fields = ("list_position", "party", "person")

    person = PersonSerializer(many=False, read_only=True)
    party = PartySerializer(many=False, read_only=True)
    list_position = serializers.SerializerMethodField(allow_null=True)

    def get_list_position(self, obj):
        """
        Needed because YNR's data model allows adding party list positions
        to ballots that don't use them. Should fix there, but this is for quick
        wins

        """
        if obj.post_election.display_as_party_list:
            return obj.list_position
        return None
