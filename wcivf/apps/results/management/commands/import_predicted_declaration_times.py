import csv
import itertools
from datetime import datetime

import pytz

from django.core.management.base import BaseCommand

from elections.models import Election, PostElection
from results.models import ResultEvent

'''
Import GE2017 declaration times as estimated by PA. One-off script,
don't reuse without fixing the time hack below.
CSV file available here:
https://docs.google.com/spreadsheets/d/1o-P27WYPRV934sgCwCBANr4a36KpJQwtwUnPdczAaI8/edit?usp=sharing
Original source:
http://election.pressassociation.com/Declaration_times/general_2017_by_name.php
'''


class Command(BaseCommand):
    help = "Import predicted declaration times from PA"

    def add_arguments(self, parser):
        parser.add_argument(
            'filename',
            help='Path to the file with expected declaration times'
        )

    def get_postelections(self, query, election):
        return PostElection.objects.filter(
            election=election,
            post__area_name=query)

    def get_constituency(self, constituency, election):
        matches = {
            'Ashton Under Lyne': 'Ashton-under-Lyne',
            'Ynys Mon': 'Ynys Môn'
        }
        if constituency in matches:
            constituency = matches[constituency]
        constituency = constituency.replace('&', 'and').strip()
        constituency = constituency.replace("Hull", "Kingston upon Hull")
        postelection = self.get_postelections(constituency, election)
        if not postelection:
            c = constituency.split()
            c.reverse()
            postelection = self.get_postelections(' '.join(c), election)
            if not postelection:
                c = constituency.split()
                c[0] = c[0] + ','
                postelection = self.get_postelections(' '.join(c), election)
                if not postelection:
                    if ', ' in constituency:
                        c = constituency.split(',')
                        postelection = self.get_postelections(
                            ' '.join([c[1], c[0]]).strip(), election)
                    if not postelection:
                        c = constituency.split()
                        for perm in itertools.permutations(c):
                            if postelection:
                                break
                            postelection = self.get_postelections(
                                ' '.join(perm), election)
        return postelection

    def handle(self, *args, **options):
        with open(options['filename'], 'r') as fh:
            reader = csv.DictReader(fh)
            election = Election.objects.get(slug='parl.2017-06-08')
            bst = pytz.timezone('Europe/London')
            for row in reader:
                results = self.get_constituency(row['constituency'], election)
                if not results:
                    print(row['constituency'], 'not found')
                postelection = results[0]
                # Hack for GE2017!
                if row['time'].startswith('23'):
                    dt = datetime.strptime('2016-06-08 %s' % row['time'],
                                           '%Y-%m-%d %H:%M')
                else:
                    dt = datetime.strptime('2016-06-09 %s' % row['time'],
                                           '%Y-%m-%d %H:%M')
                dt = bst.localize(dt)
                resultevent, _ = ResultEvent.objects.update_or_create(
                    post_election=postelection,
                    defaults={
                        'expected_declaration_time': dt
                    })
