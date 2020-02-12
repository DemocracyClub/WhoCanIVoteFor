import requests
from django.core.management.base import BaseCommand

from people.models import FacebookAdvert


class Command(BaseCommand):
    def handle(self, **options):
        url = "https://candidates.democracyclub.org.uk/api/next/facebook_adverts/?page_size=200"
        while url:
            req = requests.get(url)
            req.raise_for_status()
            results = req.json()
            self.import_ads(results.get("results", []))
            url = results.get("next")

    def import_ads(self, results):
        for result in results:
            FacebookAdvert.objects.update_or_create(
                ad_id=result["ad_id"],
                defaults={
                    "ad_json": result["ad_json"],
                    "person_id": result["person"]["id"],
                    "image_url": result["image"],
                },
            )
