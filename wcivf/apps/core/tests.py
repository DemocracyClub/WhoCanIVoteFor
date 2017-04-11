"""
Unittests for wcivf.apps.core.context_processors
"""
from django.test import TestCase
from wcivf.apps.core import context_processors

class SettingsTestCase(TestCase):
    def test_settings(self):
        from django.conf import settings

        context = context_processors.all_settings(None)

        for s in dir(settings):
            self.assertEqual(getattr(settings, s), context[s])
