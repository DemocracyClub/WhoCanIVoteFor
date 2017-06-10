class LoggerRouter(object):

    apps_that_use_logger = [
        'core',
        'feedback',
        'notifications',
    ]

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.apps_that_use_logger:
            return 'logger'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.apps_that_use_logger:
            return 'logger'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
