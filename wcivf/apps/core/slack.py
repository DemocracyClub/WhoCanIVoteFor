import random

from django.conf import settings
from slacker2 import Slacker


class SlackHelper:
    def __init__(self, user=settings.SLACK_BOT_USERNAME):
        self.FAKE_MODE = not hasattr(settings, "SLACK_TOKEN")
        if not self.FAKE_MODE:
            self.client = Slacker(settings.SLACK_TOKEN)
        self.user = user

    def post_message(
        self, to, message_text, blocks=None, attachments=None, extra_dict=None
    ):
        kwargs = {
            "username": self.user,
            "icon_emoji": ":robot_face:",
            "text": message_text,
            "attachments": attachments,
            "blocks": blocks,
        }
        if extra_dict:
            kwargs.update(extra_dict)
        if not self.FAKE_MODE:
            self.client.chat.post_message(to, **kwargs)

    @property
    def random_happy(self):
        return random.choice(
            [
                ":+1:",
                ":tada:",
                ":grinning:",
                ":heart_eyes:",
                ":heart_eyes_cat:",
                ":heart:",
                ":laughing:",
                ":sunny:",
                ":white_check_mark:",
                ":star:",
                ":smile:",
            ]
        )

    @property
    def random_sad(self):
        return random.choice(
            [
                ":-1:",
                ":disappointed:",
                ":confused:",
                ":unamused:",
                ":rage:",
                ":confounded:",
                ":hankey:",
                ":red_circle:",
                ":x:",
                ":cry:",
            ]
        )
