from rest_framework import serializers

from hustings.models import Husting


class HustingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Husting
        fields = (
            "title",
            "url",
            "starts",
            "ends",
            "location",
            "postevent_url",
        )
