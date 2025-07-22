from django.core.management.base import BaseCommand
from django.db import connection
from elections.models import VotingSystem


class Command(BaseCommand):
    def handle(self, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                BEGIN;
                TRUNCATE "auth_permission", "auth_group_permissions", "auth_user_user_permissions", "django_admin_log", "django_content_type", "django_site", "django_migrations" RESTART IDENTITY;
                COMMIT;
                """
            )
        VotingSystem.objects.all().delete()
