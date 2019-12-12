from django.conf import settings

from core.helpers import clean_postcode
from .forms import PostcodeLookupForm


def canonical_url(request):
    return {"CANONICAL_URL": settings.CANONICAL_URL}


def site_title(request):
    return {"SITE_TITLE": settings.SITE_TITLE}


def use_compress_css(request):
    return {
        "USE_COMPRESSED_CSS": getattr(settings, "USE_COMPRESSED_CSS", False)
    }


def postcode_form(request):
    return {"postcode_form": PostcodeLookupForm()}


def referer_postcode(request):
    referer_parts = request.META.get("HTTP_REFERER", "")
    referer_parts = referer_parts.strip("/").split("/")
    if len(referer_parts) >= 2 and referer_parts[-2] == "elections":
        possible_postcode = clean_postcode(referer_parts[-1])
        if len(possible_postcode) < 8:
            return {"referer_postcode": possible_postcode.replace("%20", "")}
    return {}
