import pytest

from referendums.models import Referendum


class TestReferendum:
    def test_str(self):
        question = "How should Sheffield council be run?"
        referendum = Referendum(question=question)
        assert str(referendum) == question

    @pytest.mark.parametrize(
        "campaign_urls",
        [
            {
                "answer_one_campaign_url": "https://nocampaign.com",
                "answer_two_campaign_url": "https://yescampaign.com",
            },
            {
                "answer_one_campaign_url": "https://nocampaign.com",
                "answer_two_campaign_url": "",
            },
            {
                "answer_one_campaign_url": "",
                "answer_two_campaign_url": "https://yescampaign.com",
            },
            {"answer_one_campaign_url": "", "answer_two_campaign_url": ""},
        ],
    )
    def test_campaign_urls(self, campaign_urls):
        expected = [url for _, url in campaign_urls.items() if url]
        referendum = Referendum(**campaign_urls)
        assert list(referendum.campaign_urls) == expected
