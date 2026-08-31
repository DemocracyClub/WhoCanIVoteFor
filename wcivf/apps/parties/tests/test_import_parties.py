import json

import vcr
from core.tests.helpers import TmpMediaRootMixin
from django.test import TestCase
from parties.models import Party

SINGLE_PARTY_JSON = """{
    "ec_id": "PP01",
    "url": "https://candidates.democracyclub.org.uk/api/next/parties/PP6673/",
    "name": "Wombles Alliance",
    "alternative_name": "Cynghrair Wombles",
    "register": "GB",
    "status": "Registered",
    "nations": ["ENG", "WAL", "SCO"],
    "date_registered": "2018-01-31",
    "date_deregistered": null,
    "default_emblem": {
        "image": "https://static-candidates.democracyclub.org.uk/media/cache/bf/63/bf63d47b577cfe1c8cf69a469830a847.jpg",
        "description": "Box containing the word",
        "date_approved": null,
        "ec_emblem_id": 4836,
        "default": false
    },
    "emblems": [
        {
            "image": "https://static-candidates.democracyclub.org.uk/media/cache/bf/63/bf63d47b577cfe1c8cf69a469830a847.jpg",
            "description": "Box containing the word",
            "date_approved": null,
            "ec_emblem_id": 4836,
            "default": false
        }
    ],
    "descriptions": [
        {
            "description": "Make Good Use of Bad Rubbish",
            "date_description_approved": "2018-01-31"
        }
    ],
    "legacy_slug": "party:0001"
}"""


class PartyImporterTests(TmpMediaRootMixin, TestCase):
    @vcr.use_cassette("fixtures/vcr_cassettes/test_party_import.yaml")
    def test_manager_creates_party(self):
        self.assertEqual(Party.objects.count(), 0)
        Party.objects.update_or_create_from_ynr(json.loads(SINGLE_PARTY_JSON))
        self.assertEqual(Party.objects.count(), 1)
        party = Party.objects.first()
        self.assertEqual(party.party_name, "Wombles Alliance")
        self.assertEqual(
            party.emblem_url,
            "https://static-candidates.democracyclub.org.uk/media/cache/bf/63/bf63d47b577cfe1c8cf69a469830a847.jpg",
        )

    @vcr.use_cassette("fixtures/vcr_cassettes/test_party_import.yaml")
    def test_emblem_cleared_when_party_drops_it_upstream(self):
        party_data = json.loads(SINGLE_PARTY_JSON)
        Party.objects.update_or_create_from_ynr(party_data)
        self.assertTrue(Party.objects.first().emblem_url)

        party_data["default_emblem"] = None
        Party.objects.update_or_create_from_ynr(party_data)
        self.assertIsNone(Party.objects.first().emblem_url)
