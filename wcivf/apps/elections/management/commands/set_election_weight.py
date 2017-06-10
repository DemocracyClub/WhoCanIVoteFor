from django.core.management.base import BaseCommand

from elections.models import Election


class Command(BaseCommand):
    def handle(self, **options):
        Election.objects.filter(
            slug="parl.2017-06-08").update(election_weight=100)
