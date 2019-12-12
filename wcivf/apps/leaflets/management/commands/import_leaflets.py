from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone as tz

import requests

from elections.models import PostElection
from people.models import Person
from leaflets.models import Leaflet


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, **options):
        base_url_fmt = "https://electionleaflets.org/api/ballots/{}/"
        Leaflet.objects.all().delete()
        qs = PostElection.objects.filter(election__current=True)
        for ballot in qs:
            url = base_url_fmt.format(ballot.ballot_paper_id)
            while url:
                req = requests.get(url)
                if req.status_code == 200:
                    results = req.json()
                    url = results.get("next", None)
                    self.add_leaflets(results.get("results", []))
                else:
                    url = None

    def add_leaflets(self, results):
        for leaflet in results:
            person_id = leaflet["ynr_person_id"]
            if not person_id:
                continue
            thumb_url = leaflet["first_page_thumb"]
            leaflet_id = leaflet["pk"]
            upload_date = datetime.strptime(
                leaflet["date_uploaded"].split(".")[0], "%Y-%m-%dT%H:%M:%S"
            )
            dt_aware = tz.make_aware(upload_date, tz.get_current_timezone())
            try:
                person = Person.objects.get_by_pk_or_redirect_from_ynr(
                    person_id
                )
                Leaflet.objects.create(
                    leaflet_id=leaflet_id,
                    thumb_url=thumb_url,
                    date_uploaded_to_electionleaflets=dt_aware,
                    person=person,
                )
            except Person.DoesNotExist:
                print("No person found with id %s" % person_id)
