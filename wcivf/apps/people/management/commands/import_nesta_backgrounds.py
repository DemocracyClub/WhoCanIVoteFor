"""
Importer for Nesta educational background data.
"""

import csv

from django.core.management.base import BaseCommand
from django.db import transaction
from people.models import Person


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "filename", help="Path to the file with the candidate data in it"
        )

    def update_person(self, person, row):
        for k in row:
            if row[k] == "None" or not row[k]:
                row[k] = None
        dob = row["Date of birth"]
        if dob and not person.birth_date:
            person.birth_date = dob
        if not person.gender:
            person.gender = row["Gender"]
        person.place_of_birth = row["Place of birth"]
        person.secondary_school = row["Secondary school"]
        person.university_undergrad = row["University Undergraduate Degree"]
        person.field_undergrad = row["Field Undergraduate Degree"]
        person.stem_undergrad = row["STEM Undergraduate Degree"]
        person.university_postgrad = row["University Post-graduate Degree"]
        person.field_postgrad = row["Field Post-graduate Degree"]
        person.stem_postgrad = row["STEM Post-graduate Degree"]
        person.degree_cat = row["Degree Category"]
        person.last_or_current_job = row["Last job/current job"]
        person.previously_in_parliament = row["Previously worked in parliament"]
        person.save()

    @transaction.atomic
    def handle(self, **options):
        with open(options["filename"], "r") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                ynr_id = row["ynr_id"]
                if ynr_id:
                    try:
                        person = Person.objects.get(ynr_id=ynr_id)
                        self.update_person(person, row)
                    except Person.DoesNotExist:
                        print("No person found with YNR ID %s" % ynr_id)
