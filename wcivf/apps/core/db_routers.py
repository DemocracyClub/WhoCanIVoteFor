from django_middleware_global_request import get_request


class FeedbackRouter(object):
    apps_that_use_feedback_router = ["feedback"]

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.apps_that_use_feedback_router:
            return "feedback"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.apps_that_use_feedback_router:
            return "feedback"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True


class PrincipalRDSRouter:
    def db_for_read(self, model, **hints):
        request = get_request()
        if request and request.path.startswith("/admin"):
            # read from the replica in the admin
            # to prevent race conditions
            return "principal"

        return "default"

    def db_for_write(self, model, **hints):
        return "principal"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow any relation between objects in different databases.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
