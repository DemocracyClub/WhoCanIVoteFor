import re
from datetime import datetime
from typing import List

from django import template
from django.template.defaultfilters import stringfilter
from elections.models import PostElection

register = template.Library()


@register.filter(name="ni_postcode")
@stringfilter
def ni_postcode(postcode):
    if re.match("^BT.*", postcode):
        return True
    return False


@register.filter(name="todate")
def convert_str_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


@register.filter(name="totime")
def convert_str_time(value):
    return datetime.strptime(value, "%H:%M:%S").time()


@register.filter(name="uncancelled_ballots")
def uncancelled_ballots(ballots: List[PostElection]):
    return [ballot for ballot in ballots if not ballot.cancelled]
