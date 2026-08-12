from datetime import datetime

import requests
from dateutil.parser import parse
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone as tz
from leaflets.models import Leaflet
from people.models import Person


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, **options):
        base_url = "https://electionleaflets.org/api/leaflets"

        Leaflet.objects.all().delete()
        url = f"{base_url}/?current=true"
        while url:
            print(url)
            resp = requests.get(url)
            resp.raise_for_status()
            results = resp.json()
            url = results.get("next", None)
            self.add_leaflets(results.get("results", []))

    def add_leaflets(self, results):
        for leaflet in results:
            print(leaflet["pk"])
            if "people" not in leaflet:
                continue
            for person_data in leaflet["people"]:
                person_id = list(person_data.keys())[0]
                thumb_url = leaflet["first_page_thumb"]
                leaflet_id = leaflet["pk"]
                dt_aware = self.parse_date_uploaded(leaflet["date_uploaded"])
                try:
                    person = Person.objects.get_by_pk_or_redirect_from_ynr(
                        person_id
                    )
                    Leaflet.objects.update_or_create(
                        leaflet_id=leaflet_id,
                        person=person,
                        defaults={
                            "thumb_url": thumb_url,
                            "date_uploaded_to_electionleaflets": dt_aware,
                        },
                    )
                except Person.DoesNotExist:
                    print("No person found with id %s" % person_id)

    def parse_date_uploaded(self, date_uploaded: str) -> datetime:
        dt = parse(date_uploaded)
        if dt.tzinfo is None:
            dt = tz.make_aware(dt, tz.get_current_timezone())
        else:
            dt = dt.astimezone(tz.get_current_timezone())
        return dt
