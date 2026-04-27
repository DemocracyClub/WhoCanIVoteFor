from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django_middleware_global_request import get_request

PRINCIPAL = settings.PRINCIPAL_DB_NAME
REPLICA = DEFAULT_DB_ALIAS


class PrincipalRDSRouter:
    def db_for_read(self, model, **hints):
        request = get_request()
        if request and request.path.startswith("/admin"):
            # read from the replica in the admin
            # to prevent race conditions
            return PRINCIPAL

        return REPLICA

    def db_for_write(self, model, **hints):
        return PRINCIPAL

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow any relation between objects in different databases.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
