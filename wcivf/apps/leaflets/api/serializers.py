from rest_framework import serializers

from leaflets.models import Leaflet


class LeafletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leaflet
        fields = ("leaflet_id", "thumb_url", "leaflet_url")

    leaflet_url = serializers.SerializerMethodField()

    def get_leaflet_url(self, obj: Leaflet):
        return f"https://electionleaflets.org/leaflets/{obj.leaflet_id}/"
