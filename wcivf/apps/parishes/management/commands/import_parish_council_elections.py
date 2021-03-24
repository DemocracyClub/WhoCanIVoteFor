from django.core.management.base import BaseCommand

from parishes.importers import ParishCouncilElectionImporter


class Command(BaseCommand):

    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTbfedaTDoTT3UcJOcOJHojISaSb06yzjFNvTiIUxHd7oWsN0wqFNqHXoklcTeK2G7aoUUH9NHvWy0q/pub?gid=756401424&single=true&output=csv"

    def handle(self, **options):
        importer = ParishCouncilElectionImporter(url=self.URL)
        importer.import_objects()
