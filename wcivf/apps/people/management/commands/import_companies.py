"""
Importer for all the corporate overlords
"""
import collections
import csv
import datetime
import requests

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from people.models import Person, AssociatedCompany

Company = collections.namedtuple(
    "Commpany",
    [
        "person_id",
        "name",
        "company_name",
        "company_number",
        "company_status",
        "role",
        "role_status",
        "role_appointed_date",
        "role_resigned_date",
    ],
)


def date_from_string(dt):
    """
    Given a date string DT, return a date object.
    """
    return datetime.datetime.strptime(dt, "%d %B %Y").date()


class Command(BaseCommand):
    def delete_all_companies(self):
        """
        Clear our companies away.
        """
        AssociatedCompany.objects.all().delete()

    def get_person(self, person_id):
        try:
            return Person.objects.get(ynr_id=person_id)
        except Person.DoesNotExist:
            # if this person doesn't exist in WhoCIVF
            # this could be due to a merge.
            # See if we can get an alternative person id from YNR
            url = settings.YNR_BASE + "/api/v0.9/person_redirects/" + person_id
            req = requests.get(url)
            result = req.json()

            if "new_person_id" not in result:
                # we couldn't find an alt person id, re-raise the exception
                raise

            try:
                # see if the alt person id exists
                return Person.objects.get(ynr_id=result["new_person_id"])
            except Person.DoesNotExist:
                # this person still doesn't exist in WhoCIVF
                # re-raise the exception
                raise

    def create_company(self, data):
        """
        Create an individual associated company
        """
        try:
            person = self.get_person(data.person_id)
        except Person.DoesNotExist:
            # none of our attempts to match this person id to a
            # record in our database worked: move on
            return None

        companies = AssociatedCompany.objects.filter(
            person=person, company_number=data.company_number
        )

        # We only want one reference to a company - we're not actually
        # trying to shadow Companies House
        if companies.count() == 1:
            if companies[0].role == "Director" and data.role == "Secretary":
                print("Directorship already noted")
                return companies[0]
            elif companies[0].role == "Secretary" and data.role == "Director":
                print("Updating to Director")
                company = companies[0]
            else:
                if data.company_number == companies[0].company_number:
                    print("Change of company name")
                    # Use the most recent appointment
                    data_appointed = date_from_string(data.role_appointed_date)
                    if data_appointed > companies[0].role_appointed_date:
                        company = companies[0]
                    else:
                        return companies[0]
                else:
                    print(data)
                    raise ValueError("UNKNOWN COMPANY SITUATION - DIE")
        else:
            company = AssociatedCompany(
                person=person, company_number=data.company_number
            )

        appointed = date_from_string(data.role_appointed_date)

        resigned = None
        if data.role_resigned_date:
            resigned = date_from_string(data.role_resigned_date)

        company.company_name = data.company_name
        company.company_status = data.company_status
        company.role = data.role
        company.role_appointed_date = appointed

        if resigned:
            company.role_resigned_date = resigned
        company.save()
        return company

    def get_not_associated(self, url):
        self.not_associated_companies = collections.defaultdict(set)
        req = requests.get(url)
        for line in req.text.splitlines():
            person_id, company_number = line.split(",")
            self.not_associated_companies[person_id].add(company_number)

    @transaction.atomic
    def handle(self, **options):
        """
        Entrypoint for our command.
        """
        companies_base_url = "https://raw.githubusercontent.com/EdwardBetts/companies-house/master/"
        companies_url = "{}/companies.csv".format(companies_base_url)
        not_associated_url = "{}/not_associated.csv".format(companies_base_url)

        self.get_not_associated(not_associated_url)

        self.delete_all_companies()
        counter = 0
        req = requests.get(companies_url)
        reader = csv.reader(req.text.splitlines())
        next(reader)
        for row in reader:
            try:
                data = Company(*row)
            except TypeError:
                print(row)
                raise

            if data.person_id in self.not_associated_companies:
                if (
                    data.company_number
                    in self.not_associated_companies[data.person_id]
                ):
                    # This (person, company) pair has been asserted as not connected
                    continue

            associated_company = self.create_company(data)
            if associated_company:
                counter += 1
                print(
                    "Created associated company {0} <{1}>".format(
                        counter, associated_company
                    )
                )
