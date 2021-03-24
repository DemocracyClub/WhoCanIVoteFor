from django.core.management.base import BaseCommand

from referendums.importers import ReferendumImporter


class Command(BaseCommand):

    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQHIsqVdfcZnCNgrwgtcS_ihMQbFn2S5T1ncUGKUDz2B3ONC9cUjOcdFWRtBmUxDN-f3PNEfW7bucmp/pub?gid=0&single=true&output=csv"

    def handle(self, **options):
        importer = ReferendumImporter(url=self.URL)
        importer.import_objects()
