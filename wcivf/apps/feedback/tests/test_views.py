# Test: FeedbackFormViewTests
from django.urls import reverse
from django.test import TestCase
from feedback.views import FeedbackFormView
from feedback.models import Feedback


class FeedbackFormViewTests(TestCase, FeedbackFormView):
    def setUp(self):
        self.existing_feedback = Feedback()
        self.existing_feedback.save()

    def test_token_set_by_default(self):
        request = self.client.get(reverse("feedback_form_view"))
        new_token = request.context_data["object"].token
        assert new_token
        assert new_token != self.existing_feedback.token

    def test_submit_form_saves_feedback(self):
        assert Feedback.objects.count() == 1
        req = self.client.post(
            reverse("feedback_form_view"),
            {
                "found_useful": "YES",
                "vote": "YES",
                "source_url": "https://example.com",
                "token": "123",
            },
        )
        assert req.status_code == 302
        assert Feedback.objects.count() == 2

        self.client.post(
            reverse("feedback_form_view"),
            {
                "found_useful": "YES",
                "vote": "YES",
                "source_url": "https://example.com",
                "token": "123",
            },
        )
        assert Feedback.objects.count() == 2
