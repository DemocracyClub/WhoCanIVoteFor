import csv
import requests

from elections.models import PostElection


class ReadFromUrlMixin:
    def __init__(self, url):
        self.url = url

    def read_from_url(self, url=None):
        """
        Takes optional url otherwise uses URL used in init method
        """
        url = url or self.url
        with requests.get(url, stream=True) as r:
            r.encoding = "utf-8"
            yield from csv.DictReader(r.iter_lines(decode_unicode=True))


class ReadFromFileMixin:
    def read_from_file(self, path_to_file):
        with open(path_to_file, "r") as fh:
            reader = csv.DictReader(fh)
            yield from reader


class ImportAdditionalElectionMixin(ReadFromUrlMixin):
    """
    Mixin to add shared methods used when importing some additional election
    related objects such as Referendums and ParishCouncilElections.

    As a minimum subclasses must set the model attribute and implement a
    create_object method.
    """

    model = None

    def get_ballots(self, election_id):
        """
        Returns a queryset of PostElection objects. Initially attempts to match
        a ballot_paper_id, if none found checks against Election.slug.
        """
        ballots = PostElection.objects.filter(ballot_paper_id=election_id)
        if ballots:
            return ballots

        return PostElection.objects.filter(election__slug=election_id)

    def create_object(self, row):
        raise NotImplementedError("Must be implemented on subclass")

    def import_objects(self):
        """
        Deletes existing objects to ensure we have latest data and then creates
        a new object for each row
        """
        self.model.objects.all().delete()
        for row in self.read_from_url():
            self.create_object(row=row)
