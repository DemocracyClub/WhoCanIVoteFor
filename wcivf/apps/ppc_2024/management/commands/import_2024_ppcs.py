"""
Importer for all the corporate overlords
"""

import contextlib
import csv
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from parties.models import Party
from people.models import Person
from ppc_2024.models import PPCPerson


class BlankRowException(ValueError):
    ...


def clean_party_id(party_id):
    if not party_id:
        return None
    if party_id.startswith("ynmp-party"):
        # special case, just return this ID
        # (independents or speaker)
        return party_id

    if "-" in party_id:
        if party_id.startswith("joint-party:"):
            return party_id
        return f"joint-party:{party_id}"

    return f"PP{party_id}"


@dataclass
class CSVRow:
    person_name: str
    party_id: str
    person_id: str
    constituency_name: str
    region_name: str
    sheet_row: dict

    @classmethod
    def from_csv_row(cls, row: dict):
        party_id = clean_party_id(row.pop("Party ID", None))
        if not party_id:
            raise BlankRowException("No party ID")

        person_name = row.pop("Candidate Name")
        person_id = row.pop("DC Candidate ID")
        constituency_name = row.pop("Constituency")
        region_name = row.pop("Nation / Region")

        sheet_row = row
        return cls(
            party_id=party_id,
            person_name=person_name,
            person_id=person_id,
            constituency_name=constituency_name,
            region_name=region_name,
            sheet_row=sheet_row,
        )


class Command(BaseCommand):
    def delete_all_ppcs(self):
        PPCPerson.objects.all().delete()

    def get_person(self, person_id):
        if not person_id:
            return None
        try:
            return Person.objects.get(ynr_id=person_id)
        except Person.DoesNotExist:
            # if this person doesn't exist in WCIVF
            # this could be due to a merge.
            # See if we can get an alternative person id from YNR
            url = urljoin(
                settings.YNR_BASE, f"/api/next/person_redirects/{person_id}"
            )
            req = requests.get(url)
            if req.status_code != 200:
                raise

            result = req.json()

            if "new_person_id" not in result:
                # we couldn't find an alt person id, re-raise the exception
                raise

            try:
                # see if the alt person id exists
                return Person.objects.get(ynr_id=result["new_person_id"])
            except Person.DoesNotExist:
                # this person still doesn't exist in WCIVF
                # re-raise the exception
                raise

    def create_ppc(self, data: CSVRow):
        print(data.party_id)
        party: Party = Party.objects.get(ec_id=data.party_id)

        person: Optional[Person] = None
        with contextlib.suppress(Person.DoesNotExist):
            person = self.get_person(data.person_id)

        return PPCPerson.objects.create(
            person_name=data.person_name,
            party=party,
            person=person,
            constituency_name=data.constituency_name,
            region_name=data.region_name,
            sheet_row=data.sheet_row,
        )

    @transaction.atomic
    def handle(self, **options):
        self.delete_all_ppcs()
        counter = 0
        req = requests.get(PPCPerson.CSV_URL)
        reader: List[Dict] = csv.DictReader(
            req.content.decode("utf8").splitlines()
        )
        for row in reader:
            try:
                data = CSVRow.from_csv_row(row)
                self.create_ppc(data)
            except (BlankRowException, ValueError):
                self.stderr.write(f"Error importing row: {row}")
                continue

            counter += 1
        print(counter)
