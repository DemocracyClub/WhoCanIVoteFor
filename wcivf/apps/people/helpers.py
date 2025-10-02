import contextlib
import time

import requests

from .models import PersonPost


def get_wikipedia_extract(wikipedia_url):
    base_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
    wiki_title = wikipedia_url.strip("/").split("/")[-1]
    url = "{}{}".format(base_url, wiki_title)

    print(url)

    """
    WikiMedia want us to:
    - Include a User-Agent header that makes it easy for them to contact us if our usage is abusive
    - Stay under 200 requests per second

    200 requests per second is a very generous rate limit and is
    unlocked by specifying a User-Agent in their requested format
    (i.e: not 'python-requests/2.31.0')
    Just making sequential requests we shouldn't
    need to sleep at all to stay under this limit but we implement sleep
    behaviour if we get a `429 Too Many Requests` back for completeness

    https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
    https://en.wikipedia.org/api/rest_v1/
    """
    headers = {
        "User-Agent": "DemocracyClubBot/1.0 (https://democracyclub.org.uk/contact/; developers@democracyclub.org.uk)"
    }
    resp = requests.get(url, headers=headers)

    """
    If we hit a 429, respect the retry-after header
    https://wikitech.wikimedia.org/wiki/Robot_policy#Generally_applicable_rules
    """
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After")
        # default: if we fail to parse a sensible value
        # out of the headers just sleep for a second
        sleep_time = 1
        if retry_after is not None:
            with contextlib.suppress(ValueError):
                # we expect this to be expressed as aa number of second to wait for
                # not a datetime to retry after
                # https://www.mediawiki.org/wiki/Manual:Maxlag_parameter
                sleep_time = int(retry_after)
        time.sleep(sleep_time)
        resp = requests.get(url, headers=headers)

    if resp.status_code == 404:
        return ""

    resp.raise_for_status()
    data = resp.json()
    return data.get("extract", "")


def peopleposts_for_election_post(election, post):
    return PersonPost.objects.filter(election=election, post=post)
