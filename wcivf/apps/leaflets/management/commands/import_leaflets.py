from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone as tz
from django.utils.http import urlencode
from elections.models import PostElection
from leaflets.models import Leaflet
from people.models import Person


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--recently-uploaded",
            action="store_true",
            dest="recently_uploaded",
            help="Import leaflets uploaded since last imported Leaflet",
        )
        parser.add_argument(
            "--uploaded-since",
            action="store",
            dest="uploaded_since",
            help="Import leaflets uploaded since last imported Leaflet",
        )

    @transaction.atomic
    def handle(self, **options):
        base_url = "https://electionleaflets.org/api/leaflets"

        qs = PostElection.objects.filter(election__current=True)
        if options["recently_uploaded"]:
            # delete non current leaflets
            Leaflet.objects.exclude(
                person__personpost__post_election__in=qs
            ).delete()

            latest_upload = Leaflet.objects.order_by(
                "-date_uploaded_to_electionleaflets"
            ).first()

            since = options.get("uploaded_since", None)
            if since and " " not in since:
                since = f"{since} 00:00"
            if not since:
                try:
                    since = latest_upload.date_uploaded_to_electionleaflets
                except AttributeError:
                    since = None

            params = {}
            if since:
                params = {"modified__gt": since}
            url = f"{base_url}/?{urlencode(params)}"
            while url:
                req = requests.get(url)
                req.raise_for_status()
                results = req.json()
                url = results.get("next", None)
                self.add_leaflets(results.get("results", []))
        else:
            Leaflet.objects.all().delete()
            for ballot in qs:
                url = f"{base_url}/?ballot={ballot.ballot_paper_id}"
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
        upload_date = datetime.strptime(
            date_uploaded.split(".")[0], "%Y-%m-%dT%H:%M:%S"
        )
        return tz.make_aware(upload_date, tz.get_current_timezone())
